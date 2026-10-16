import asyncio
import os
from datetime import datetime, timedelta, timezone

from course_alerts.deadline_alerts import evaluate_deadline_alert
from course_alerts.models import CourseState, DeadlineAlertRequest, LearnerState


async def main() -> None:
    phone = os.environ.get("DEMO_LEARNER_PHONE")
    if not phone:
        raise RuntimeError("DEMO_LEARNER_PHONE is required")

    now = datetime.now(timezone.utc)
    request = DeadlineAlertRequest(
        alert_id=f"demo-{now.strftime('%Y%m%d%H%M')}",
        course_code="PY-201",
        course_state=CourseState.LIVE,
        learner_state=LearnerState.ACTIVE,
        learner_phone=phone,
        deadline_at=now + timedelta(hours=12),
        evaluated_at=now,
    )
    report = await evaluate_deadline_alert(request)
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())

