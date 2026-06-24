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
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import JSONResponse
        from pydantic import BaseModel, Field
    except ImportError as exc:
        raise RuntimeError(
            "Install server extras to run the HTTP service: "
            "pip install 'moctale-moderation[server]'"
        ) from exc

    from .engine import ModerationEngine
    from .schemas import ModerationRequest

    engine: ModerationEngine | None = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # type: ignore[type-arg]
        """Manage engine lifecycle — warm up on startup, teardown on shutdown."""
        nonlocal engine
        engine = ModerationEngine()
        yield
        engine = None

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
    def moderate(comment: CommentRequest) -> dict[str, Any]:
        """Moderate a single comment.

        Args:
            comment: Comment request body.

        Returns:
            ModerationResult as a dict.
        """
        assert engine is not None
        request = ModerationRequest(**comment.model_dump())
        return engine.analyze(request).to_dict()

    @app.post("/moderate/batch", tags=["moderation"])
    async def moderate_batch(batch: BatchRequest) -> dict[str, list[dict[str, Any]]]:
        """Moderate a batch of comments (up to 256). Uses async concurrency.

        Args:
            batch: Batch request body containing a list of comment requests.

        Returns:
            Dict with 'results' key containing list of ModerationResult dicts.
        """
        assert engine is not None
        requests = [ModerationRequest(**c.model_dump()) for c in batch.comments]
        results = await engine.analyze_many_async(requests)
        return {"results": [r.to_dict() for r in results]}

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
