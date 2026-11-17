import logging
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError
from pydantic import ValidationError

from config import BASE_DIR, GEMINI_MODELS, GEMINI_TIMEOUT_SECONDS

load_dotenv(BASE_DIR / ".env")
load_dotenv()

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    """Create the Gemini client on first use, so the app can start (and the
    tests can run) even when no API key is configured."""

    global _client

    if _client is None:

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set")

        # Structured output (JSON mode) is only available on the v1beta API.
        _client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                api_version="v1beta",
                timeout=GEMINI_TIMEOUT_SECONDS * 1000,     # milliseconds
            ),
        )

    return _client


# ---------------- model fallback ---------------- #

def _should_try_next_model(error: Exception) -> bool:
    """Problems that another model may not have: overload, quota, a retired
    model, a hung request. A bad request or a bad key is OUR problem, so it is
    raised immediately instead of being retried on every model."""

    if isinstance(error, ServerError):                       # 5xx, e.g. 503 high demand
        return True

    if isinstance(error, ClientError):
        return error.code in (404, 429)                      # retired model / quota

    return "timeout" in type(error).__name__.lower()


def generate_with_fallback(*, contents, config=None, client=None, models=None):
    """generate_content() on the first model that works.

    Returns (response, model_name). If every model fails, the last error is raised.
    """

    client = client or _get_client()
    last_error = None

    for model in (models or GEMINI_MODELS):

        try:
            response = client.models.generate_content(model=model, contents=contents, config=config)
            logger.info("Gemini model used: %s", model)
            return response, model

        except Exception as error:
            if not _should_try_next_model(error):
                raise

            logger.warning("Model %s is unavailable (%s); trying the next one", model, type(error).__name__)
            last_error = error

    raise last_error


def generate_response(prompt):

    try:
        logger.info("Sending request to Gemini API")

        response, _ = generate_with_fallback(contents=prompt)

        logger.info("Gemini response generated successfully")

        return response.text

    except RuntimeError:
        logger.error("GEMINI_API_KEY is missing - AI analysis is disabled")

        return (
            "AI analysis is not configured. Add GEMINI_API_KEY to "
            "backend/.env and restart the server."
        )

    except ServerError:
        logger.exception("Gemini service is temporarily unavailable")

        return (
            "AI analysis is temporarily unavailable due to high demand. "
            "Please try again later."
        )

    except ClientError:
        logger.exception("Gemini API request failed")

        return "AI analysis could not be generated due to an API request error."

    except Exception:
        logger.exception("Unexpected error while calling Gemini")

        return "AI analysis is temporarily unavailable. Please try again later."


MAX_STRUCTURED_ATTEMPTS = 2


def _friendly_error(error: Exception) -> str:
    """Same user-facing messages as generate_response()."""

    if isinstance(error, RuntimeError):
        return (
            "AI analysis is not configured. Add GEMINI_API_KEY to "
            "backend/.env and restart the server."
        )

    if isinstance(error, ServerError):
        return (
            "AI analysis is temporarily unavailable due to high demand. "
            "Please try again later."
        )

    if isinstance(error, ClientError):
        return "AI analysis could not be generated due to an API request error."

    return "AI analysis is temporarily unavailable. Please try again later."


def generate_structured(prompt, schema):
    """Ask Gemini for JSON that matches a Pydantic model (structured output).

    Returns (result, error_message): exactly one of them is None.
    The reply is validated with Pydantic; if it does not match the schema the
    call is retried once before giving up.
    """

    last_error = None

    for attempt in range(1, MAX_STRUCTURED_ATTEMPTS + 1):

        try:
            logger.info("Requesting structured output (attempt %d)", attempt)

            response, _ = generate_with_fallback(
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.2,          # low = more consistent output
                ),
            )

            # response.parsed is filled in by the SDK; validate the raw text
            # ourselves as a safety net so a bad reply can never get through.
            return schema.model_validate_json(response.text), None

        except ValidationError as error:
            logger.warning("Structured output did not match the schema: %s", error)
            last_error = error
            continue                           # retry once

        except Exception as error:
            logger.exception("Structured generation failed")
            return None, _friendly_error(error)

    return None, _friendly_error(last_error)
