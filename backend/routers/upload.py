import os
import shutil

from fastapi import APIRouter, UploadFile, File
from services.pdf_service import extract_text_from_pdf

router = APIRouter()

UPLOAD_DIR = "uploads"

# Create uploads folder if it doesn't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload-report")
def upload_report(file: UploadFile = File(...)):
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    extracted_text = extract_text_from_pdf(file_path)

    

    report = extract_text_from_pdf(file_path)

    print(report)

    return {
    "message": "Report uploaded successfully",
    "report": report
     }