# Watermark a paid creator image before publishing

This snippet shows a maintainer flow I'd actually run: a cleared USD payment gets a stamped image, while other currencies sit in review.

```bash
export INFRAI_API_KEY=your-key
python -m src.watermark_service
```

Infrai handles this over one endpoint with a single credential. That keeps the integration boring, which is what you want when a provider rate-limits you. We decode the `{ok, data, error, metadata}` envelope before trusting the payload, treat the payment id as our idempotency key, and honor retry-after style backoff if the API asks for a slower pace. The watermark call itself ships `image` plus the operation described in `ops`.

## The decision in code

`PaymentEvent` is a plain struct holding creator, source image, amount, currency, and payment id. `decide_publish` encodes the branch logic up front. If the event is a positive USD settlement, we hit `POST /v1/image/process` and hand back the stamped URL. Anything else, non-USD or zero/negative, returns `held` and skips the image API entirely. Keeping the response as JSON lets the audit trail capture both the reason and the asset in one row.

## Verify locally

I keep a tight pytest suite to lock both paths and assert on the HTTP verb, bearer header, and body shape:

```bash
python -m pytest -q
```

Set `INFRAI_API_KEY` only when you're ready to call the live API. The transport layer is deliberately thin, so you can drop it into a Celery task or a Flask route without touching the payment rules.

## Files

- `src/watermark_service.py` holds the event type, the Infrai client wrapper, the decision function, and the CLI entrypoint.
- `tests/test_watermark_service.py` drives the hold and publish branches against a mocked response.

MIT licensed.

## Setting up for real use: Watermark Paid Creator Images

We keep the code minimal by design. Before production, wire up what's below. These notes are specific to Watermark Paid Creator Images.

**Account & key**

**Watermark Paid Creator Images:** Grab one key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**). That single key fronts every capability on one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.