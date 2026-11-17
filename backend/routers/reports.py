from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response

from models.auth_models import ReportDetail, ReportSummary
from services import report_storage_service as storage
from services.auth_service import CurrentUser, get_current_user

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=List[ReportSummary])
def list_my_reports(user: CurrentUser = Depends(get_current_user)):
    return storage.list_reports(user_id=user.id)


@router.get("/{report_id}", response_model=ReportDetail)
def get_my_report(report_id: str, user: CurrentUser = Depends(get_current_user)):

    try:
        return storage.load_report(report_id, user_id=user.id)
    except storage.ReportNotFoundError:
        raise HTTPException(status_code=404, detail="Report not found.")


@router.delete("/{report_id}", status_code=204)
def delete_my_report(report_id: str, user: CurrentUser = Depends(get_current_user)):

    try:
        storage.delete_report(report_id, user_id=user.id)
    except storage.ReportNotFoundError:
        raise HTTPException(status_code=404, detail="Report not found.")

    return Response(status_code=204)
