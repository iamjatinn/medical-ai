from pydantic import BaseModel


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
    findings: list[Finding]
    ai_summary: str


class ReportResponse(BaseModel):
    message: str
    result: ReportResult