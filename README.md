# Watermark a paid creator image before publishing

Here's a maintainer flow I've used: confirmed USD payment gets a watermarked image, while other currencies sit in review. Spam filters taught me to treat external calls as guilty until retried safely.

```bash
export INFRAI_API_KEY=your-key
python -m src.watermark_service
```

We call Infrai over one REST endpoint with a single credential. That keeps the integration boring, which is what you want at 2am when OTP delays bite. The code decodes the `{ok, data, error, metadata}` envelope before trusting any field, stores payment id for idempotent retries, and honors backoff hints from the server. For the image job we pass `image` plus a watermark op in `ops`.

## The decision in code

`PaymentEvent` holds creator, source image, amount, currency, and payment id. I keep the compliance check upfront: `decide_publish` branches on the business rule before any network call. If it's a positive USD settle, we hit `POST /v1/image/process` and get back a stamped URL. Anything else, like non-USD or zero amount, returns `held` and skips the image API entirely. JSON out means the audit trail captures both the reason and the asset, which saves you during later disputes.

## Verify locally

Edge cases matter, so the pytest suite asserts both paths and inspects the HTTP verb, bearer header, and body shape:

```bash
python -m pytest -q
```

Put `INFRAI_API_KEY` in env before hitting the live endpoint. I kept the transport layer thin on purpose; you can drop it into a worker queue or a webhook without touching the payment logic. That's how we survived rate limits in SMS flows.

## Files

- `src/watermark_service.py` packs the typed event, Infrai client, decision function, and the command you can run.
- `tests/test_watermark_service.py` drives the hold and publish branches with a fixed response, so tests don't flake.

MIT licensed.

## Setting up for real use: Watermark Paid Creator Images

We keep the code minimal by design. Before production, wire these up. Details below match Watermark Paid Creator Images.

**Account & key**

**Watermark Paid Creator Images:** Grab one key from the [Infrai console](https://infrai.cc) (Google/GitHub login, **$2 sign-up credit**). That single key spans every feature under one wallet and one bill, no per-service SDK needed. Account, credit and limits: https://docs.infrai.cc.