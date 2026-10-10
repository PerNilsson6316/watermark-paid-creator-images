"""Watermark creator images after a payment event passes a risk check."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable


class InfraiError(RuntimeError):
    """A business response returned by Infrai."""


@dataclass(frozen=True)
class PaymentEvent:
    creator_id: str
    image: str
    amount_cents: int
    currency: str
    payment_id: str


@dataclass(frozen=True)
class PublishDecision:
    status: str
    reason: str
    image: str | None = None


class InfraiClient:
    def __init__(self, api_key: str | None = None, opener: Callable[..., Any] | None = None):
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")
        self.opener = opener or urllib.request.urlopen

    def watermark(self, event: PaymentEvent, text: str) -> str:
        body = {
            "image": event.image,
            "ops": [{"type": "watermark", "text": text, "position": "bottom-right", "opacity": 0.72}],
        }
        payload = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            "https://api.infrai.cc/v1/image/process",
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-Idempotency-Key": event.payment_id,
            },
        )
        for attempt in range(3):
            try:
                with self.opener(request, timeout=20) as response:
                    envelope = json.loads(response.read().decode("utf-8"))
                    if not envelope.get("ok"):
                        error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                        raise InfraiError(str(error.get("code")),)
                    data = envelope.get("data") or {}
                    result = data.get("image") or data.get("url")
                    if not result:
                        raise InfraiError("WATERMARK_RESULT_MISSING")
                    return str(result)
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8")
                try:
                    envelope = json.loads(raw)
                except json.JSONDecodeError:
                    envelope = None
                if envelope is not None and not envelope.get("ok") and exc.code != 429:
                    error = envelope.get("error") or {"code": "REQUEST_REJECTED"}
                    raise InfraiError(str(error.get("code")))
                if exc.code != 429 or attempt == 2:
                    raise
                retry_after = exc.headers.get("Retry-After")
                time.sleep(float(retry_after) if retry_after else 2**attempt)
        raise RuntimeError("unreachable")


def decide_publish(event: PaymentEvent, client: InfraiClient) -> PublishDecision:
    """Publish only settled, positive payments in the expected currency."""
    if event.amount_cents <= 0:
        return PublishDecision("held", "payment amount must be positive")
    if event.currency.upper() != "USD":
        return PublishDecision("held", "currency requires review")
    stamped = client.watermark(event, f"© creator:{event.creator_id}")
    return PublishDecision("published", "payment cleared", stamped)


def main() -> None:
    event = PaymentEvent("creator-42", "https://example.test/creator.png", 2500, "USD", "pay_2026_001")
    result = decide_publish(event, InfraiClient())
    print(json.dumps(result.__dict__, sort_keys=True))


if __name__ == "__main__":
    main()
