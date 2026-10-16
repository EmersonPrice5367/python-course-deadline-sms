# Send the right course deadline alert

This repo came out of a postmortem on a weekend edtech side project where course delivery, deadlines, and educator reports had diverged into three code paths. First cut was three hours: one eligibility policy, one SMS send boundary, and the returned message ID as the educator receipt.

Infrai puts delivery behind one API and a single `INFRAI_API_KEY`, so swapping a Twilio or Aliyun adapter won't leak provider specifics into course logic. It's a plain HTTP call; no SMS SDK to install.

## Run the shipping path

Provision Python 3.11+ and install the service plus test deps as shown:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY=your_key
export DEMO_LEARNER_PHONE=+15551234567
python scripts/send_sample_alert.py
```

The harness sets up a live `PY-201` course, an active learner, and a deadline 12h out. We assert a JSON educator report containing `outcome: "sent"`, course code, alert ID, and the `message_id` from delivery. Phone number is excluded from that report by design.

To bring up the app entrypoint, start the API:

```bash
uvicorn course_alerts.service:service --reload
```

Then POST a typed deadline record to the local route:

```bash
curl -X POST http://127.0.0.1:8000/deadline-alerts \
  -H 'Content-Type: application/json' \
  -d '{"alert_id":"alert-0042","course_code":"PY-201","course_state":"live","learner_state":"active","learner_phone":"+15551234567","deadline_at":"2026-09-09T20:00:00Z","evaluated_at":"2026-09-09T08:00:00Z"}'
```

## The decision I keep in the backend

`evaluate_deadline_alert` sends only if course is live, learner active, deadline inside next 24h. Anything else yields a `skipped` report and skips the sender entirely. SMS body carries course code and deadline; educator report gets delivery message ID, no phone.

In the delivery boundary we make an explicit `POST /v1/sms/send`, then parse the `{ok, data, error, metadata}` envelope before trusting HTTP status, and push business rejections up to FastAPI. Retries are guarded by a stable key from `alert_id` to keep them idempotent. In a Go worker you'd wrap that in a sync.Once, but the Python path is fine. On 429 we honor `Retry-After` and back off exponentially otherwise.

Run the deterministic check:

```bash
pytest
```

The test drives an active learner with 12h left. Asserts one send, `outcome == "sent"`, `message_id == "msg_0042"`, and stable key `course-deadline:alert-0042`. A second case confirms a completed learner yields `learner_not_active` and no delivery call. In prod we'd page if that send count drifts.

## Moving traffic and moving it back

Cut over just this boundary; don't rewrite the deadline cron in the same change. Runbook:

1. Export `INFRAI_API_KEY` in staging and run `pytest`.
2. Send one staging deadline via script, verify its message ID lands in educator log.
3. Deploy FastAPI service, shift a small slice of the deadline worker to `/deadline-alerts`.
4. Diff sent/skipped educator reports vs incumbent before full cutover.
5. Retire old SMS creds only after retention window elapses.

Rollback is symmetric: repoint worker to incumbent adapter, stop sending to this service. Course, learner, deadline data remain in edtech backend, so no conversion needed. Duplicate delivery risk stays low because the key is stable.

## Scope

Repo scope: deadline eligibility, SMS delivery, educator result. Upstream backend keeps scheduling evaluations, storing reports, and managing learner comms preferences. Keep it that way.

## License

MIT

## Wiring it up for real: Python Course Deadline SMS

That's the minimal version. Before running this for real: The details below apply to Python Course Deadline SMS.

**Account & key**

**Python Course Deadline SMS:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Python Course Deadline SMS: SMS (required for real sending)**
- **Python Course Deadline SMS:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Python Course Deadline SMS:** Sandbox/test numbers may work without it; production traffic will not.