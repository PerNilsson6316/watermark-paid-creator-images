import json

from src.watermark_service import InfraiClient, PaymentEvent, decide_publish


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps({"ok": True, "data": {"image": "https://cdn.test/stamped.png"}}).encode()


def test_non_usd_payment_is_held_without_calling_api():
    calls = []

    def opener(*_args, **_kwargs):
        calls.append(True)
        return FakeResponse()

    event = PaymentEvent("c1", "img", 1200, "EUR", "pay-eur")
    result = decide_publish(event, InfraiClient("test-key", opener))
    assert result.status == "held"
    assert result.reason == "currency requires review"
    assert calls == []


def test_cleared_payment_sends_watermark_request():
    seen = {}

    def opener(request, **_kwargs):
        seen["method"] = request.method
        seen["body"] = json.loads(request.data)
        seen["auth"] = request.headers["Authorization"]
        return FakeResponse()

    event = PaymentEvent("c1", "img", 1200, "USD", "pay-usd")
    result = decide_publish(event, InfraiClient("test-key", opener))
    assert result.status == "published"
    assert seen == {
        "method": "POST",
        "body": {"image": "img", "ops": [{"type": "watermark", "text": "© creator:c1", "position": "bottom-right", "opacity": 0.72}]},
        "auth": "Bearer test-key",
    }
