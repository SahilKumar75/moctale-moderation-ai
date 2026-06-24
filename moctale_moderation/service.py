"""Optional FastAPI HTTP service for Moctale Moderation AI.

Install extras to use: pip install moctale-moderation[server]

Run::

    uvicorn moctale_moderation.service:app --reload

Endpoints:
    GET  /health           — Basic liveness check
    GET  /health/ready     — Readiness + cache stats
    POST /moderate         — Moderate a single comment
    POST /moderate/batch   — Moderate up to 256 comments concurrently
    GET  /policy/version   — Current policy version info
"""
from __future__ import annotations

import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any


def create_app() -> Any:
    """Create and configure the FastAPI application.

    Returns:
        A fully configured FastAPI app instance.

    Raises:
        RuntimeError: If fastapi or pydantic are not installed.
    """
    try:

        from fastapi import FastAPI, Request, Response
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import JSONResponse
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
        from pydantic import BaseModel, Field
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

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[type-arg]
        nonlocal engine, cache, audit
        engine = ModerationEngine()
        cache = ModerationCache(redis_url=os.getenv("REDIS_URL"))
        audit = AuditLogger()
        yield
        engine = None
        cache = None
        audit = None

    class CommentRequest(BaseModel):
        """Single comment moderation request body."""

        text: str = Field(min_length=1, max_length=2000, description="Comment text to moderate")
        context_type: str = Field(default="reply_to_review", description="Placement context")
        parent_review_rating: str = Field(default="Skip", description="Parent review rating")
        movie_rating_perfection_pct: float = Field(default=90.0, ge=0, le=100)
        movie_rating_skip_pct: float = Field(default=5.0, ge=0, le=100)
        model_toxicity_score: float | None = Field(default=None, ge=0, le=1)

    class BatchRequest(BaseModel):
        """Batch comment moderation request body."""

        comments: list[CommentRequest] = Field(min_length=1, max_length=256)

    class FeedbackRequest(BaseModel):
        """Human moderator feedback for a previously processed comment."""

        text_hash: str = Field(description="SHA-256 hash of the original comment text")
        human_action: str = Field(
            pattern="^(allow|flag_for_review|flag_for_removal)$",
            description="Human moderator's corrected action",
        )
        moderator_id: str = Field(default="anonymous")

    app = FastAPI(
        title="Moctale Moderation AI",
        version="0.2.0",
        description=(
            "Production-grade multilingual comment moderation "
            "for Indian movie review platforms."
        ),
        lifespan=lifespan,
    )


    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        req_id = str(uuid.uuid4())
        request.state.req_id = req_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response


    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        """Basic liveness check.

        Returns:
            JSON with 'status' and 'version' keys.
        """
        return {"status": "ok", "version": "0.2.0"}

    @app.get("/health/ready", tags=["system"])
    def ready() -> dict[str, Any]:
        """Readiness check — confirms engine is warmed up.

        Returns:
            503 if engine is not ready, otherwise 200 with cache stats.
        """
        if engine is None:
            return JSONResponse(status_code=503, content={"status": "not_ready"})
        cache = engine.cache_info()
        return {
            "status": "ready",
            "cache_hits": cache.hits,
            "cache_misses": cache.misses,
        }


    @app.post("/moderate", tags=["moderation"])
    @track_latency()
    def moderate(comment: CommentRequest, request: Request) -> dict[str, Any]:
        assert engine is not None
        req_id = getattr(request.state, "req_id", None)
        
        # Check cache
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
            category=result.predicted_category
        ).inc()
            
        res_dict = result.to_dict()
        if cache:
            cache.set(comment.text, comment.context_type, res_dict)
            
        return res_dict

    @app.post("/moderate/batch", tags=["moderation"])
    @track_latency()
    async def moderate_batch(batch: BatchRequest, request: Request) -> dict[str, list[dict[str, Any]]]:
        assert engine is not None
        req_id = getattr(request.state, "req_id", None)
        requests = [ModerationRequest(**c.model_dump()) for c in batch.comments]
        
        t0 = time.time()
        results = await engine.analyze_many_async(requests)
        latency_ms = (time.time() - t0) * 1000
        
        res_dicts = []
        for c, r in zip(batch.comments, results):
            if audit:
                audit.log_decision(c.text, c.context_type, r, latency_ms / len(results), req_id)
            MODERATION_DECISIONS_TOTAL.labels(
                action=r.predicted_action, 
                category=r.predicted_category
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
        return {"items": []} # Stub for Phase 5 UI

    @app.post("/feedback", tags=["moderation"])
    def submit_feedback(feedback: FeedbackRequest) -> dict[str, str]:
        """Accept human moderator feedback for policy improvement (stub).

        Args:
            feedback: Feedback request body.

        Returns:
            Acknowledgment dict. Extended in Phase 4 to persist feedback.
        """
        return {"status": "accepted", "text_hash": feedback.text_hash}

    @app.get("/policy/version", tags=["policy"])
    def policy_version() -> dict[str, Any]:
        """Return current policy version info (stub — extended in Phase 4).

        Returns:
            Dict with version, rule_count, and backend fields.
        """
        return {"version": "1.0.0", "rule_count": 0, "backend": "heuristic"}

    return app


# ---------------------------------------------------------------------------
# ASGI entry point for uvicorn: uvicorn moctale_moderation.service:app
# ---------------------------------------------------------------------------

try:
    app = create_app()
except RuntimeError:
    # FastAPI not installed — service module loaded but app is None.
    # Install with: pip install 'moctale-moderation[server]'
    app = None  # type: ignore[assignment]
