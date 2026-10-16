import asyncio
from datetime import datetime, timedelta, timezone

from course_alerts.deadline_alerts import evaluate_deadline_alert
from course_alerts.models import (
    CourseState,
    DeadlineAlertRequest,
    LearnerState,
    SmsReceipt,
)


NOW = datetime(2026, 9, 9, 8, 0, tzinfo=timezone.utc)


def alert(**changes: object) -> DeadlineAlertRequest:
    values: dict[str, object] = {
        "alert_id": "alert-0042",
        "course_code": "PY-201",
        "course_state": CourseState.LIVE,
        "learner_state": LearnerState.ACTIVE,
        "learner_phone": "+15551234567",
        "deadline_at": NOW + timedelta(hours=12),
        "evaluated_at": NOW,
    }
    values.update(changes)
    return DeadlineAlertRequest.model_validate(values)


def test_active_learner_inside_window_gets_one_reportable_alert() -> None:
    calls: list[dict[str, str]] = []

    async def record_send(**payload: str) -> SmsReceipt:
        calls.append(payload)
        return SmsReceipt(message_id="msg_0042")

    report = asyncio.run(evaluate_deadline_alert(alert(), sender=record_send))

    assert report.model_dump(exclude_none=True) == {
        "outcome": "sent",
        "alert_id": "alert-0042",
        "course_code": "PY-201",
        "message_id": "msg_0042",
    }
    assert calls == [
        {
            "to": "+15551234567",
            "message": "Course PY-201: your learning deadline is 2026-09-09T20:00:00+00:00.",
            "idempotency_key": "course-deadline:alert-0042",
        }
    ]


def test_completed_learner_is_skipped_without_delivery() -> None:
    async def unexpected_send(**payload: str) -> SmsReceipt:
        raise AssertionError(f"unexpected delivery: {payload}")

    report = asyncio.run(
        evaluate_deadline_alert(
            alert(learner_state=LearnerState.COMPLETED), sender=unexpected_send
        )
    )

    assert report.outcome == "skipped"
    assert report.reason == "learner_not_active"
