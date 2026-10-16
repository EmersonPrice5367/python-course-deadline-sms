from collections.abc import Awaitable, Callable
from .models import (
    CourseState,
    DeadlineAlertRequest,
    EducatorReport,
    LearnerState,
    SmsReceipt,
)


SmsSender = Callable[..., Awaitable[SmsReceipt]]


async def evaluate_deadline_alert(
    request: DeadlineAlertRequest,
    sender: SmsSender | None = None,
) -> EducatorReport:
    if request.course_state is not CourseState.LIVE:
        return _skipped(request, "course_not_live")
    if request.learner_state is not LearnerState.ACTIVE:
        return _skipped(request, "learner_not_active")

    hours_remaining = (
        request.deadline_at - request.evaluated_at
    ).total_seconds() / 3600
    if hours_remaining <= 0 or hours_remaining > 24:
        return _skipped(request, "outside_reminder_window")

    if sender is None:
        from .infrai_sms import send_transactional_sms

        sender = send_transactional_sms

    receipt = await sender(
        to=request.learner_phone,
        message=(
            f"Course {request.course_code}: your learning deadline is "
            f"{request.deadline_at.isoformat()}."
        ),
        idempotency_key=f"course-deadline:{request.alert_id}",
    )
    return EducatorReport(
        outcome="sent",
        alert_id=request.alert_id,
        course_code=request.course_code,
        message_id=receipt.message_id,
    )


def _skipped(request: DeadlineAlertRequest, reason: str) -> EducatorReport:
    return EducatorReport(
        outcome="skipped",
        alert_id=request.alert_id,
        course_code=request.course_code,
        reason=reason,
    )
