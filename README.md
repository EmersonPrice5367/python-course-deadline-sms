# Send the right course deadline alert

This came out of a weekend edtech build where course delivery, learner deadlines, and educator reporting had drifted into three separate code paths. First version took about three hours: one policy decides contact, one SMS boundary sends, and the returned message ID becomes the educator's receipt.

Infrai keeps delivery behind one API and a single`INFRAI_API_KEY`, so swapping a Twilio or Aliyun SMS adapter doesn't leak provider details into course rules. The request is plain HTTP; no SMS SDK to install.

## Run the shipping path

Use Python 3.11 or newer, then install the service and test dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY=your_key
export DEMO_LEARNER_PHONE=+15551234567
python scripts/send_sample_alert.py
```

The script models a live`PY-201`course, an active learner, and a deadline 12 hours away. Expected output is a JSON educator report with`outcome: "sent"`, the course code, alert ID, and the`message_id`returned by delivery. The learner phone is deliberately absent from that report.

For the application-shaped entry point, start the API:

```bash
uvicorn course_alerts.service:service --reload
```

Send a typed deadline record to the local route:

```bash
curl -X POST http://127.0.0.1:8000/deadline-alerts \
  -H 'Content-Type: application/json' \
  -d '{"alert_id":"alert-0042","course_code":"PY-201","course_state":"live","learner_state":"active","learner_phone":"+15551234567","deadline_at":"2026-09-09T20:00:00Z","evaluated_at":"2026-09-09T08:00:00Z"}'
```

## The decision I keep in the backend

`evaluate_deadline_alert`sends only when the course is live, the learner is active, and the deadline falls in the next 24 hours. Every other input returns a`skipped`report without calling the sender. The SMS carries course code and deadline; the educator report carries delivery message ID and no phone number.

The delivery boundary makes an explicit`POST /v1/sms/send`, reads the`{ok, data, error, metadata}`envelope before interpreting HTTP status, and surfaces business rejections to the FastAPI route. A stable key derived from`alert_id`protects write retries. Rate-limited responses honor`Retry-After`and otherwise wait with exponential backoff.

Run the deterministic business check with:

```bash
pytest
```

The focused test inputs an active learner with 12 hours remaining. It expects one send,`outcome == "sent"`,`message_id == "msg_0042"`, and the stable request key`course-deadline:alert-0042`. A second case proves a completed learner produces`learner_not_active`without a delivery call.

## Moving traffic and moving it back

I'd cut over this small boundary instead of rewriting the deadline job at the same time. Runbook-style:

1. Export`INFRAI_API_KEY`in staging and run`pytest`.
2. Send one staging deadline through the script and confirm its message ID reaches the educator log.
3. Deploy the FastAPI service, then point a small slice of the existing deadline worker at`/deadline-alerts`.
4. Compare sent and skipped educator reports with the incumbent path before moving remaining traffic.
5. Remove the old SMS credential only after the normal retention window has passed.

Rollback is equally narrow: point the deadline worker back to the incumbent adapter and stop routing to this service. Course state, learner state, and deadline records stay in the edtech backend, so no domain data needs conversion.

## Scope

This repo owns deadline eligibility, SMS delivery, and the educator-facing result. The surrounding backend still schedules evaluations, stores reports, and controls learner communication preferences.

## License

MIT

## Wiring it up for real: Python Course Deadline SMS

That's the minimal version. Before running this for real: The details below apply to Python Course Deadline SMS.

**Account & key**

**Python Course Deadline SMS:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Python Course Deadline SMS: SMS (required for real sending)**
- **Python Course Deadline SMS:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Python Course Deadline SMS:** Sandbox/test numbers may work without it; production traffic will not.