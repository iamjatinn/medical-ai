from typing import List, Optional

from pydantic import BaseModel


class ReferenceRange(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None


class Finding(BaseModel):
    parameter: str
    value: float
    unit: str
    reference_range: ReferenceRange
    reported_status: Optional[str] = None
    calculated_status: str
    status_match: Optional[bool] = None


class ReportResult(BaseModel):
    report_id: str
    filename: str
    created_at: str
    findings: List[Finding]
    ai_summary: str


class ReportResponse(BaseModel):
    message: str
    result: ReportResult
