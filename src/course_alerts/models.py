from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class CourseState(str, Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    ENDED = "ended"


class LearnerState(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    WITHDRAWN = "withdrawn"


class DeadlineAlertRequest(BaseModel):
    alert_id: str = Field(min_length=8, max_length=100)
    course_code: str = Field(min_length=2, max_length=32)
    course_state: CourseState
    learner_state: LearnerState
    learner_phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    deadline_at: datetime
    evaluated_at: datetime


class EducatorReport(BaseModel):
    outcome: str
    alert_id: str
    course_code: str
    reason: str | None = None
    message_id: str | None = None


class SmsReceipt(BaseModel):
    message_id: str

