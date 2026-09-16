from pydantic import BaseModel
from typing import List


class ReferenceRange(BaseModel):
    min: float
    max: float


class Finding(BaseModel):
    parameter: str
    value: float
    unit: str
    reference_range: ReferenceRange
    reported_status: str
    calculated_status: str
    status_match: bool


class ReportResult(BaseModel):
    report_id: str
    filename: str
    created_at: str
    findings: List[Finding]
    ai_summary: str


class ReportResponse(BaseModel):
    message: str
    result: ReportResult