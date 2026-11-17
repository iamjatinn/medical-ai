import logging
import os

from dotenv import load_dotenv
from google import genai
from google.genai.errors import ClientError, ServerError

from config import BASE_DIR, GEMINI_MODEL

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

        _client = genai.Client(api_key=api_key)

    return _client


def generate_response(prompt):

    try:
        logger.info("Sending request to Gemini API")

        response = _get_client().models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )

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
