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


@router.post(
    "/upload-report",
    response_model=ReportResponse
)
def upload_report(file: UploadFile = File(...)):

    logger.info(f"Received file: {file.filename}")

    if file.content_type != "application/pdf":

        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed."
        )

    try:

        file_path = os.path.join(
            UPLOAD_DIR,
            file.filename
        )

        with open(file_path, "wb") as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

        result = process_medical_report(file_path)

        return {
            "message": "Report uploaded successfully",
            "result": result
        }

    except Exception as e:

        logger.exception(e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )