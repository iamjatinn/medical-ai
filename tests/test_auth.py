import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import helpers

import jwt
from fastapi.testclient import TestClient

import config
import database
import main
from models.db_models import User
from routers import auth as auth_router
from routers import chat as chat_router
from routers import upload as upload_router
from services import auth_service
from services import report_storage_service as storage
from services.rate_limit import RateLimiter


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class RateLimiterTests(unittest.TestCase):

    def test_blocks_after_the_limit_and_recovers_after_the_window(self):

        clock = FakeClock()
        limiter = RateLimiter(3, window_seconds=60, clock=clock)

        self.assertTrue(all(limiter.try_acquire("a") for _ in range(3)))
        self.assertFalse(limiter.try_acquire("a"))
        self.assertTrue(limiter.try_acquire("b"))                # other keys are independent

        clock.now += 61                                           # window passed
        self.assertTrue(limiter.try_acquire("a"))

    def test_reset_and_retry_after(self):

        clock = FakeClock()
        limiter = RateLimiter(1, window_seconds=60, clock=clock)
        limiter.record("k")

        self.assertTrue(limiter.is_limited("k"))
        self.assertTrue(0 < limiter.retry_after("k") <= 61)

        limiter.reset("k")
        self.assertFalse(limiter.is_limited("k"))


class PasswordAndTokenTests(unittest.TestCase):

    def test_password_is_hashed_and_verifiable(self):

        hashed = auth_service.hash_password("my-secret-pass")

        self.assertNotIn("my-secret-pass", hashed)
        self.assertTrue(hashed.startswith("$2"))                  # bcrypt
        self.assertTrue(auth_service.verify_password("my-secret-pass", hashed))
        self.assertFalse(auth_service.verify_password("wrong-pass", hashed))
        self.assertNotEqual(hashed, auth_service.hash_password("my-secret-pass"))   # random salt

    def test_valid_token_round_trip(self):
        self.assertEqual(auth_service.decode_access_token(auth_service.create_access_token(42)), 42)

    def test_expired_tampered_and_foreign_tokens_are_rejected(self):

        expired = auth_service.create_access_token(1, expires_minutes=-1)
        self.assertIsNone(auth_service.decode_access_token(expired))

        good = auth_service.create_access_token(1)
        self.assertIsNone(auth_service.decode_access_token(good[:-3] + "abc"))      # tampered signature

        foreign = jwt.encode(
            {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "some-other-secret", algorithm="HS256",
        )
        self.assertIsNone(auth_service.decode_access_token(foreign))

        unsigned = jwt.encode(
            {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            None, algorithm="none",
        )
        self.assertIsNone(auth_service.decode_access_token(unsigned))              # "alg: none" attack

        no_expiry = jwt.encode({"sub": "1"}, config.JWT_SECRET, algorithm="HS256")
        self.assertIsNone(auth_service.decode_access_token(no_expiry))

        self.assertIsNone(auth_service.decode_access_token("not.a.token"))


class AuthApiTests(unittest.TestCase):

    def setUp(self):
        helpers.patch_database(self)
        helpers.fresh_limiters(self)
        self.client = TestClient(main.app)

    def login(self, email, password):
        return self.client.post("/auth/login", data={"username": email, "password": password})

    # ---------------- register / login ---------------- #

    def test_register_login_and_me(self):

        headers, user_id = helpers.register(self.client, "Alice@Example.com", "correct-horse-1")

        me = self.client.get("/auth/me", headers=headers)
        self.assertEqual(me.json(), {"id": user_id, "email": "alice@example.com"})   # email normalised

        login = self.login("alice@example.com", "correct-horse-1")
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.json()["token_type"], "bearer")

    def test_password_is_never_stored_in_plain_text(self):

        helpers.register(self.client, "alice@example.com", "correct-horse-1")

        with database.SessionLocal() as session:
            stored = session.query(User).one().password_hash

        self.assertNotIn("correct-horse-1", stored)
        self.assertTrue(stored.startswith("$2"))

    def test_duplicate_email_is_rejected(self):

        helpers.register(self.client, "alice@example.com")

        again = self.client.post("/auth/register", json={"email": "ALICE@example.com", "password": "another-pass-1"})
        self.assertEqual(again.status_code, 409)

    def test_weak_or_invalid_registration_input_is_rejected(self):

        for body in (
            {"email": "alice@example.com", "password": "short"},
            {"email": "alice@example.com", "password": "x" * 80},
            {"email": "not-an-email", "password": "long-enough-1"},
            {"email": "", "password": "long-enough-1"},
        ):
            self.assertEqual(self.client.post("/auth/register", json=body).status_code, 422, body)

    def test_wrong_password_and_unknown_email_give_the_same_answer(self):

        helpers.register(self.client, "alice@example.com", "correct-horse-1")

        wrong_password = self.login("alice@example.com", "wrong-password")
        unknown_email = self.login("nobody@example.com", "whatever-pass")

        self.assertEqual(wrong_password.status_code, 401)
        self.assertEqual(unknown_email.status_code, 401)
        self.assertEqual(wrong_password.json(), unknown_email.json())     # no account enumeration

    def test_repeated_failed_logins_are_throttled(self):

        helpers.register(self.client, "alice@example.com", "correct-horse-1")

        statuses = [self.login("alice@example.com", "wrong-password").status_code for _ in range(12)]

        self.assertEqual(statuses[:10], [401] * 10)
        self.assertEqual(statuses[10:], [429, 429])

        # even the right password is refused while throttled
        self.assertEqual(self.login("alice@example.com", "correct-horse-1").status_code, 429)

    # ---------------- every protected route needs a token ---------------- #

    def test_protected_routes_reject_missing_or_bad_tokens(self):

        calls = [
            ("get", "/auth/me", {}),
            ("get", "/reports", {}),
            ("get", "/reports/11111111-1111-4111-8111-111111111111", {}),
            ("delete", "/reports/11111111-1111-4111-8111-111111111111", {}),
            ("post", "/chat", {"json": {"report_id": "x", "question": "hi"}}),
            ("post", "/upload-report", {"files": {"file": ("a.pdf", b"%PDF-1", "application/pdf")}}),
        ]

        for method, path, kwargs in calls:
            self.assertEqual(getattr(self.client, method)(path, **kwargs).status_code, 401, path)

            bad = getattr(self.client, method)(path, headers={"Authorization": "Bearer garbage"}, **kwargs)
            self.assertEqual(bad.status_code, 401, path)

    def test_token_of_a_deleted_user_stops_working(self):

        headers, user_id = helpers.register(self.client)

        with database.SessionLocal() as session:
            session.delete(session.get(User, user_id))
            session.commit()

        self.assertEqual(self.client.get("/auth/me", headers=headers).status_code, 401)


class DataIsolationTests(unittest.TestCase):
    """The most important tests: users must not see each other's data."""

    def setUp(self):
        helpers.patch_database(self)
        helpers.fresh_limiters(self)
        self.client = TestClient(main.app)

        self.alice, self.alice_id = helpers.register(self.client, "alice@example.com")
        self.bob, self.bob_id = helpers.register(self.client, "bob@example.com")

        self.report = storage.save_report(
            "alice-private.pdf",
            [{"parameter": "Hemoglobin", "value": 11.2, "unit": "g/dL",
              "reference_range": {"min": 13.5, "max": 17.5}, "calculated_status": "Low"}],
            "alice's secret summary", user_id=self.alice_id,
        )
        self.url = f"/reports/{self.report['report_id']}"

    def test_owner_can_list_open_and_chat(self):

        listed = self.client.get("/reports", headers=self.alice).json()
        self.assertEqual([r["filename"] for r in listed], ["alice-private.pdf"])

        opened = self.client.get(self.url, headers=self.alice)
        self.assertEqual(opened.status_code, 200)
        self.assertEqual(opened.json()["ai_summary"], "alice's secret summary")

        with mock.patch("services.agent_service.run_agent",
                        return_value={"answer": "hi alice", "tools_used": [], "steps": 1}):
            chat = self.client.post("/chat", headers=self.alice,
                                    json={"report_id": self.report["report_id"], "question": "hello"})
        self.assertEqual(chat.status_code, 200)

    def test_other_user_cannot_see_open_chat_with_or_delete_it(self):

        self.assertEqual(self.client.get("/reports", headers=self.bob).json(), [])

        self.assertEqual(self.client.get(self.url, headers=self.bob).status_code, 404)

        chat = self.client.post("/chat", headers=self.bob,
                                json={"report_id": self.report["report_id"], "question": "show me everything"})
        self.assertEqual(chat.status_code, 404)

        self.assertEqual(self.client.delete(self.url, headers=self.bob).status_code, 404)

        # Alice's report is untouched and its chat history stayed empty
        still_there = self.client.get(self.url, headers=self.alice)
        self.assertEqual(still_there.status_code, 200)
        self.assertEqual(still_there.json()["chat_history"], [])

    def test_a_forbidden_report_looks_exactly_like_a_missing_one(self):
        """404 for both, so nobody can probe which report ids exist."""

        forbidden = self.client.get(self.url, headers=self.bob)
        missing = self.client.get("/reports/11111111-1111-4111-8111-111111111111", headers=self.bob)

        self.assertEqual(forbidden.status_code, missing.status_code)
        self.assertEqual(forbidden.json(), missing.json())

    def test_owner_can_delete_their_report(self):

        self.assertEqual(self.client.delete(self.url, headers=self.alice).status_code, 204)
        self.assertEqual(self.client.get(self.url, headers=self.alice).status_code, 404)
        self.assertEqual(self.client.get("/reports", headers=self.alice).json(), [])

    def test_upload_and_chat_are_rate_limited_per_user(self):

        with mock.patch.object(upload_router, "upload_limiter", RateLimiter(1, 3600)), \
             mock.patch.object(chat_router, "chat_limiter", RateLimiter(1, 3600)), \
             mock.patch("services.agent_service.run_agent",
                        return_value={"answer": "ok", "tools_used": [], "steps": 1}), \
             mock.patch("services.medical_report_service.explain_report",
                        return_value={"summary": "s", "analysis": None}):

            body = {"report_id": self.report["report_id"], "question": "hi"}
            self.assertEqual(self.client.post("/chat", json=body, headers=self.alice).status_code, 200)
            self.assertEqual(self.client.post("/chat", json=body, headers=self.alice).status_code, 429)

            # a different user has their own allowance
            self.assertEqual(self.client.post("/chat", json=body, headers=self.bob).status_code, 404)

            files = {"file": ("r.pdf", helpers.SAMPLE_PDF.read_bytes(), "application/pdf")}
            self.assertEqual(self.client.post("/upload-report", files=files, headers=self.alice).status_code, 200)
            self.assertEqual(self.client.post("/upload-report", files=files, headers=self.alice).status_code, 429)


if __name__ == "__main__":
    unittest.main()
