"""Optional FastAPI HTTP service for Moctale Moderation AI.

Install extras to use: pip install moctale-moderation[server]

Run::

    uvicorn moctale_moderation.service:app --reload

Endpoints:
    GET  /health           — Basic liveness check
    GET  /health/ready     — Readiness + cache stats
    POST /moderate         — Moderate a single comment (requires X-API-Key if MODERATION_API_KEY set)
    POST /moderate/batch   — Moderate up to 256 comments concurrently
    GET  /policy/version   — Current policy version info

Auth:
    Set MODERATION_API_KEY env var to enable API key auth.
    Pass the key as X-API-Key request header.
    When unset, auth is skipped (dev mode).

CORS:
    Set ALLOWED_ORIGINS env var (comma-separated) to restrict origins.
    Defaults to http://localhost:3000 in dev. Set to your domain in prod.

Rate limits:
    POST /moderate       — 60 requests / minute per IP
    POST /moderate/batch — 10 requests / minute per IP
"""
from __future__ import annotations

import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any


def create_app() -> Any:
    """Create and configure the FastAPI application."""
    try:
        from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import JSONResponse
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
        from pydantic import BaseModel, Field
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        from slowapi.util import get_remote_address
    except ImportError as exc:
        raise RuntimeError(
            "Install server extras to run the HTTP service: "
            "pip install 'moctale-moderation[server]'"
        ) from exc

    from .audit import AuditLogger
    from .cache import ModerationCache
    from .engine import ModerationEngine
    from .metrics import MODERATION_DECISIONS_TOTAL, track_latency
    from .schemas import ModerationRequest

    engine: ModerationEngine | None = None
    cache: ModerationCache | None = None
    audit: AuditLogger | None = None

    # --- Auth ---
    _API_KEY = os.getenv("MODERATION_API_KEY")

    async def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
        if _API_KEY and x_api_key != _API_KEY:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")

    # --- Rate limiter ---
    limiter = Limiter(key_func=get_remote_address)

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[type-arg]
        nonlocal engine, cache, audit
        engine = ModerationEngine()
        cache = ModerationCache(redis_url=os.getenv("REDIS_URL"))
        engine.set_cache(cache)
        audit = AuditLogger()
        yield
        engine = None
        cache = None
        audit = None

    class CommentRequest(BaseModel):
        text: str = Field(min_length=1, max_length=2000, description="Comment text to moderate")
        context_type: str = Field(default="reply_to_review", description="Placement context")
        parent_review_rating: str = Field(default="Skip", description="Parent review rating")
        movie_rating_perfection_pct: float = Field(default=90.0, ge=0, le=100)
        movie_rating_skip_pct: float = Field(default=5.0, ge=0, le=100)
        model_toxicity_score: float | None = Field(default=None, ge=0, le=1)

    class BatchRequest(BaseModel):
        comments: list[CommentRequest] = Field(min_length=1, max_length=256)

    class FeedbackRequest(BaseModel):
        text_hash: str = Field(description="SHA-256 hash of the original comment text")
        human_action: str = Field(
            pattern="^(allow|flag_for_review|flag_for_removal)$",
            description="Human moderator's corrected action",
        )
        moderator_id: str = Field(default="anonymous")

    allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

    app = FastAPI(
        title="Moctale Moderation AI",
        version="0.2.0",
        description=(
            "Production-grade multilingual comment moderation "
            "for Indian movie review platforms."
        ),
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-API-Key"],
    )

    @app.middleware("http")
    async def add_request_id(request: Request, call_next: Any) -> Any:
        req_id = str(uuid.uuid4())
        request.state.req_id = req_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.2.0"}

    @app.get("/health/ready", tags=["system"])
    def ready() -> dict[str, Any]:
        if engine is None:
            return JSONResponse(status_code=503, content={"status": "not_ready"})
        info = engine.cache_info()
        return {
            "status": "ready",
            "cache_hits": info.hits,
            "cache_misses": info.misses,
        }

    @app.post("/moderate", tags=["moderation"], dependencies=[Depends(verify_api_key)])
    @track_latency()
    @limiter.limit("60/minute")
    def moderate(comment: CommentRequest, request: Request) -> dict[str, Any]:
        if engine is None:
            raise HTTPException(status_code=503, detail="Moderation engine not ready")
        req_id = getattr(request.state, "req_id", None)

        if cache:
            cached = cache.get(comment.text, comment.context_type)
            if cached:
                return cached

        req = ModerationRequest(**comment.model_dump())
        t0 = time.time()
        result = engine.analyze(req)
        latency_ms = (time.time() - t0) * 1000

        if audit:
            audit.log_decision(comment.text, comment.context_type, result, latency_ms, req_id)

        MODERATION_DECISIONS_TOTAL.labels(
            action=result.predicted_action,
            category=result.predicted_category,
        ).inc()

        res_dict = result.to_dict()
        if cache:
            cache.set(comment.text, comment.context_type, res_dict)

        return res_dict

    @app.post("/moderate/batch", tags=["moderation"], dependencies=[Depends(verify_api_key)])
    @track_latency()
    @limiter.limit("10/minute")
    async def moderate_batch(
        batch: BatchRequest, request: Request
    ) -> dict[str, list[dict[str, Any]]]:
        if engine is None:
            raise HTTPException(status_code=503, detail="Moderation engine not ready")
        req_id = getattr(request.state, "req_id", None)
        requests_list = [ModerationRequest(**c.model_dump()) for c in batch.comments]

        t0 = time.time()
        results = await engine.analyze_many_async(requests_list)
        latency_ms = (time.time() - t0) * 1000

        res_dicts = []
        for c, r in zip(batch.comments, results):
            if audit:
                audit.log_decision(c.text, c.context_type, r, latency_ms / len(results), req_id)
            MODERATION_DECISIONS_TOTAL.labels(
                action=r.predicted_action,
                category=r.predicted_category,
            ).inc()
            d = r.to_dict()
            res_dicts.append(d)
            if cache:
                cache.set(c.text, c.context_type, d)

        return {"results": res_dicts}

    @app.get("/metrics", tags=["system"])
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/review-queue", tags=["moderation"])
    def review_queue() -> dict[str, Any]:
        return {"items": []}

    @app.post("/feedback", tags=["moderation"])
    def submit_feedback(feedback: FeedbackRequest) -> dict[str, str]:
        from .agents.learning_agent import LearningAgent
        LearningAgent.record_feedback(
            text_hash=feedback.text_hash,
            human_action=feedback.human_action,
            moderator_id=feedback.moderator_id,
        )
        return {"status": "accepted", "text_hash": feedback.text_hash}

    @app.get("/policy/version", tags=["policy"])
    def policy_version() -> dict[str, Any]:
        return {"version": "1.0.0", "rule_count": 0, "backend": "heuristic+rag"}

    return app


# ---------------------------------------------------------------------------
# ASGI entry point for uvicorn: uvicorn moctale_moderation.service:app
# ---------------------------------------------------------------------------

try:
    app = create_app()
except RuntimeError:
    app = None  # type: ignore[assignment]
