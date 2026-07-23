import os
import logging

from dotenv import load_dotenv
from google import genai
from google.genai.errors import ServerError, ClientError

load_dotenv()

logger = logging.getLogger(__name__)

api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)


def generate_response(prompt):

    try:
        logger.info("Sending request to Gemini API")

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        logger.info("Gemini response generated successfully")

        return response.text

    except ServerError:
        logger.exception("Gemini service is temporarily unavailable")

        return (
            "AI analysis is temporarily unavailable due to high demand. "
            "Please try again later."
        )

    except ClientError:
        logger.exception("Gemini API request failed")

        return (
            "AI analysis could not be generated due to an API request error."
        )

    except Exception:
        logger.exception("Unexpected error while calling Gemini")

        return (
            "AI analysis is temporarily unavailable. "
            "Please try again later."
        )