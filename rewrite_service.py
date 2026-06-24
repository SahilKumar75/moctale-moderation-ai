import re
with open("moctale_moderation/service.py", "r") as f:
    content = f.read()

# Replace imports
imports = """
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any
"""
content = re.sub(r"from contextlib import asynccontextmanager\nfrom typing import Any\n", imports, content)

# Add FastAPI imports inside try block
fastapi_imports = """
        from fastapi import FastAPI, Request, Response
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import JSONResponse
        from pydantic import BaseModel, Field
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
"""
content = re.sub(r"        from fastapi import FastAPI\n        from fastapi\.middleware\.cors import CORSMiddleware\n        from fastapi\.responses import JSONResponse\n        from pydantic import BaseModel, Field\n", fastapi_imports, content)

# Replace engine initialization and lifespan
lifespan_code = """
    from .engine import ModerationEngine
    from .schemas import ModerationRequest
    from .cache import ModerationCache
    from .audit import AuditLogger
    from .metrics import track_latency, MODERATION_DECISIONS_TOTAL

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
"""
content = re.sub(r"    from \.engine import ModerationEngine.*?    @asynccontextmanager\n    async def lifespan\(app: FastAPI\):.*?\n        engine = None\n", lifespan_code, content, flags=re.DOTALL)

# Add request ID middleware
middleware_code = """
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
"""
content = content.replace("""    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )""", middleware_code)

# Update moderate endpoint
moderate_code = """
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
"""
content = re.sub(r"    @app\.post\(\"/moderate\", tags=\[\"moderation\"\]\).*?    @app\.post\(\"/moderate/batch\", tags=\[\"moderation\"\]\).*?    return {\"results\": \[r\.to_dict\(\) for r in results\]}\n", moderate_code, content, flags=re.DOTALL)

# Add metrics and review-queue endpoints
new_endpoints = """
    @app.get("/metrics", tags=["system"])
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/review-queue", tags=["moderation"])
    def review_queue() -> dict[str, Any]:
        return {"items": []} # Stub for Phase 5 UI
"""
content = content.replace('    @app.post("/feedback"', new_endpoints + '\n    @app.post("/feedback"')

with open("moctale_moderation/service.py", "w") as f:
    f.write(content)
