from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import clip_routes, job_routes, upload_routes
from app.config import (
    CLEANUP_ON_STARTUP,
    CORS_ORIGINS,
    SPOTTER_V2_CHECKPOINT_PATH,
    SPOTTER_V2_THRESHOLDS_PATH,
    ensure_directories,
)
from app.pipeline.feature_extractor import preflight_soccernet_extractor
from app.services.cleanup_service import cleanup_stale_artifacts


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_directories()
    if CLEANUP_ON_STARTUP:
        cleanup_stale_artifacts()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Football Highlight Cutter API",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    app.include_router(upload_routes.router, tags=["upload"])
    app.include_router(job_routes.router, tags=["jobs"])
    app.include_router(clip_routes.router, tags=["clips"])

    @app.get("/health")
    def health():
        missing_model_files = [
            path
            for path in (SPOTTER_V2_CHECKPOINT_PATH, SPOTTER_V2_THRESHOLDS_PATH)
            if not os.path.isfile(path)
        ]

        soccernet_error = None
        soccernet_runtime = None
        try:
            soccernet_runtime = preflight_soccernet_extractor()
        except Exception as exc:  # Health endpoint must report, not crash.
            soccernet_error = str(exc)

        ready = soccernet_error is None and not missing_model_files
        return {
            "status": "ok" if ready else "not_ready",
            "pipeline": "football_highlight_detection",
            "ready": ready,
            "soccernet_ready": soccernet_error is None,
            "soccernet_runtime": soccernet_runtime,
            "soccernet_error": soccernet_error,
            "model_ready": not missing_model_files,
            "missing_model_artifacts": missing_model_files,
        }

    return app


app = create_app()
