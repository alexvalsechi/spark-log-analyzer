"""
Spark Log Analyzer — FastAPI entrypoint.
Applies: Dependency Injection, clean controller delegation.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from .api.routes import router
from .oauth_routes import router as oauth_router
from .utils.config import get_settings
from .utils.logging_config import setup_logging

settings = get_settings()

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logging.getLogger(__name__).info("Spark Log Analyzer starting up…")
    yield
    logging.getLogger(__name__).info("Shutting down…")


app = FastAPI(
    title="Spark Log Analyzer",
    description="Reduce and analyze Apache Spark event logs with AI-powered diagnostics.",
    version="2.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
app.include_router(oauth_router, prefix="/api")


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/", include_in_schema=False)
def landing_page():
    return FileResponse(FRONTEND_DIR / "sprklogs-landing.html")


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


