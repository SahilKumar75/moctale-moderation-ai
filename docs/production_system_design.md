# Production System Design

## Goal

Serve target-aware moderation for reviews and replies with low latency, low compute, and predictable cost.

## Request Flow

1. API receives a review or reply.
2. Cheap validation rejects empty or oversized text.
3. A warm `ModerationEngine` normalizes text, reuses compiled regexes, runs phrase indexes, and returns a policy decision.
4. Optional model inference runs only for risky or uncertain comments.
5. `allow` comments return inline. `flag_for_review` and `flag_for_removal` also enqueue an audit event for moderators.

## Components

- Edge/API: FastAPI or the host framework's HTTP layer.
- Policy engine: `moctale_moderation.ModerationEngine`, loaded once per process.
- Optional ML scorer: ONNX or quantized DistilBERT service, called only when cheap heuristics cannot decide confidently.
- Queue: Kafka, Redis Streams, SQS, or the hosted platform equivalent for audit and moderator workflows.
- Cache: in-process LRU for repeated comments; Redis only if repeated cross-process traffic is high.
- Storage: append-only moderation decisions and feature snapshots for audits and retraining.
- Observability: p50/p95/p99 latency, action distribution, model-call rate, cache-hit rate, false-positive review samples.

## Low-Cost Execution Strategy

- Keep rule and phrase state immutable and warm in memory.
- Run deterministic DSA-style gates first: token set lookup, phrase buckets, and target detection.
- Avoid model calls for clear safe movie criticism and clear severe abuse.
- Batch optional model calls in micro-batches of 16 to 64 comments when traffic is high.
- Cap batch endpoint size to protect memory and tail latency.
- Use async request handling for I/O and a bounded worker pool if CPU-heavy model inference is enabled.
- Prefer ONNX quantization for the toxicity model before scaling to larger instances.

## Concurrency Notes

`ModerationEngine` is safe to share across threads because its policy data is immutable and request state is local. The LRU cache is implemented by Python's `functools.lru_cache`, which is internally coherent for concurrent access in CPython.

## Scaling Path

- One small API instance can serve the pure policy engine at very high throughput.
- Scale horizontally by CPU once optional model inference is enabled.
- Keep model workers separate if p99 API latency matters.
- Use autoscaling on request rate, queue depth, and p95 latency.

## Production Guardrails

- Treat removals as recommendations until moderation policy and appeals are finalized.
- Store reason codes with every decision for auditability.
- Re-evaluate thresholds on real consent-cleared Moctale traffic.
- Track language-mix breakdowns so Hinglish and Hindi performance does not hide inside aggregate metrics.
