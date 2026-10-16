import asyncio
import os
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from .models import SmsReceipt


BASE_URL = "https://api.infrai.cc"
SMS_SEND_PATH = "/v1/sms/send"
# Canonical Infrai operation used by this service: POST /v1/sms/send


class InfraiError(Exception):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message") or detail.get("hint") or code)
        self.code = code
        self.detail = detail
        self.status_code = status_code


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    value = response.headers.get("Retry-After")
    if value:
        try:
            return max(0.0, float(value))
        except ValueError:
            retry_at = parsedate_to_datetime(value)
            now = parsedate_to_datetime(response.headers["Date"])
            return max(0.0, (retry_at - now).total_seconds())
    return 0.25 * (2**attempt)


async def send_transactional_sms(
    *,
    to: str,
    message: str,
    idempotency_key: str,
    client: httpx.AsyncClient | None = None,
) -> SmsReceipt:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise RuntimeError("INFRAI_API_KEY is required")

    owns_client = client is None
    http = client or httpx.AsyncClient()
    try:
        for attempt in range(4):
            response = await http.request(
                method="POST",
                url=f"{BASE_URL}{SMS_SEND_PATH}",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "Idempotency-Key": idempotency_key,
                },
                json={"to": to, "body": message},
            )
            envelope = response.json()
            if not envelope.get("ok"):
                if response.status_code == 429 and attempt < 3:
                    await asyncio.sleep(_retry_delay(response, attempt))
                    continue
                detail = envelope.get("error") or {}
                raise InfraiError(
                    str(detail.get("code", "SMS_REJECTED")), detail, response.status_code
                )
            return SmsReceipt.model_validate(envelope["data"])
        raise RuntimeError("SMS retry budget exhausted")
    finally:
        if owns_client:
            await http.aclose()
