import os
import shutil
import logging

from fastapi import APIRouter, UploadFile, File, HTTPException
from models.response_models import ReportResponse
from services.medical_report_service import process_medical_report

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = "uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload-report", response_model=ReportResponse)
def upload_report(file: UploadFile = File(...)):

    logger.info(f"Received file: {file.filename}")

    # Allow only PDF files
    if file.content_type != "application/pdf":
        logger.warning(f"Invalid file type uploaded: {file.content_type}")

        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )

    try:

        file_path = os.path.join(UPLOAD_DIR, file.filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"File saved successfully: {file_path}")

        result = process_medical_report(file_path)

        logger.info("Medical report processed successfully.")

        return {
            "message": "Report uploaded successfully",
            "result": result
        }

    except Exception:

        logger.exception("Error while processing medical report.")

        raise HTTPException(
            status_code=500,
            detail="Internal server error while processing the report."
        )