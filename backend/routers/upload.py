import logging
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from config import MAX_UPLOAD_MB, UPLOAD_DIR, UPLOADS_PER_HOUR_PER_USER
from models.response_models import ReportResponse
from services.auth_service import CurrentUser, get_current_user
from services.medical_report_service import process_medical_report
from services.rate_limit import RateLimiter

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

CHUNK_BYTES = 1024 * 1024


# file type -> (content type, first bytes). PDFs are read as text; scans and photos by the AI.
ALLOWED_FILES = {
    ".pdf": ("application/pdf", b"%PDF-"),
    ".png": ("image/png", b"\x89PNG"),
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
}


def _display_name(filename: str | None) -> str:
    """Keep only the file name (no folders) for display purposes."""

    name = re.split(r"[\\/]", filename or "")[-1].strip()

    return name or "report.pdf"


upload_limiter = RateLimiter(UPLOADS_PER_HOUR_PER_USER, window_seconds=60 * 60)


@router.post("/upload-report", response_model=ReportResponse)
def upload_report(file: UploadFile = File(...), user: CurrentUser = Depends(get_current_user)):

    # Each upload costs AI quota, so limit how many one user can send.
    if not upload_limiter.try_acquire(user.id):
        raise HTTPException(status_code=429, detail="Upload limit reached. Please try again later.")

    display_name = _display_name(file.filename)

    logger.info("Received file: %s", display_name)

    extension = Path(display_name.lower()).suffix
    allowed = ALLOWED_FILES.get(extension)

    if allowed is None or file.content_type != allowed[0]:
        raise HTTPException(status_code=400, detail="Only PDF, PNG or JPG files are allowed.")

    # The client-supplied name is never used on disk: a random name rules out
    # overwriting files or writing outside the uploads folder.
    saved_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{extension}"

    try:

        size = 0

        with open(saved_path, "wb") as buffer:

            while chunk := file.file.read(CHUNK_BYTES):

                if size == 0 and not chunk.startswith(allowed[1]):
                    raise HTTPException(
                        status_code=400,
                        detail="The file is not a valid PDF, PNG or JPG.",
                    )

                size += len(chunk)

                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File is too large (limit {MAX_UPLOAD_MB} MB).",
                    )

                buffer.write(chunk)

        if size == 0:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")

        result = process_medical_report(saved_path, original_filename=display_name, user_id=user.id)

        return {"message": "Report uploaded successfully", "result": result}

    except HTTPException:
        raise

    except ValueError as error:
        # Problems with the document itself (scanned, no results, ...)
        logger.warning("Could not process %s: %s", display_name, error)
        raise HTTPException(status_code=422, detail=str(error))

    except Exception:
        logger.exception("Unexpected error while processing %s", display_name)
        raise HTTPException(
            status_code=500,
            detail="Something went wrong while processing the report.",
        )

    finally:
        # Medical documents should not pile up on disk.
        saved_path.unlink(missing_ok=True)
