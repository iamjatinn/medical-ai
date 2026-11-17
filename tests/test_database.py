import unittest

import helpers  # noqa: F401

import database


class DatabaseUrlTests(unittest.TestCase):

    def test_provider_urls_get_the_psycopg_driver(self):

        self.assertEqual(
            database.normalize_url("postgres://u:p@host:5432/db?sslmode=require"),
            "postgresql+psycopg://u:p@host:5432/db?sslmode=require",
        )
        self.assertEqual(
            database.normalize_url("postgresql://u:p@host/db"),
            "postgresql+psycopg://u:p@host/db",
        )

    def test_other_urls_are_left_alone(self):

        for url in ("postgresql+psycopg://u:p@db:5432/x", "sqlite:///file.db", "sqlite://"):
            self.assertEqual(database.normalize_url(url), url)


if __name__ == "__main__":
    unittest.main()
