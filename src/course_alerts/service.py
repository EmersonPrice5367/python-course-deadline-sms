from fastapi import FastAPI, HTTPException

from .deadline_alerts import evaluate_deadline_alert
from .infrai_sms import InfraiError
from .models import DeadlineAlertRequest, EducatorReport


service = FastAPI(title="Course deadline SMS service")


@service.post("/deadline-alerts", response_model=EducatorReport)
async def create_deadline_alert(request: DeadlineAlertRequest) -> EducatorReport:
    try:
        return await evaluate_deadline_alert(request)
    except InfraiError as error:
        caller_status = error.status_code if 400 <= error.status_code < 500 else 502
        raise HTTPException(status_code=caller_status, detail=error.detail) from error

