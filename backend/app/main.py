import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, brand, copy, demo, export, graphics, health, history, images, marketing, photo_assistant
from app.core.config import get_settings
from app.core.errors import AppError
from app.database.db import describe_database
from app.services.storage_service import get_storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("zorvi")

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Database: %s", describe_database())
    if settings.brevo_configured:
        logger.info("Email: sending through the Brevo API (sender %s)", settings.brevo_sender_email or "NOT SET")
    elif settings.smtp_configured:
        logger.info("Email: sending through SMTP %s:%s", settings.smtp_host, settings.smtp_port)
    else:
        logger.warning("Email: no email service configured, so emails are only PRINTED in this terminal, not sent.")
    # Uploaded files are temporary: remove anything older than FILE_TTL_HOURS on startup.
    removed = get_storage().cleanup_expired(settings.file_ttl_hours)
    if removed:
        logger.info("Removed %d expired file(s)", removed)
    yield


app = FastAPI(
    title=f"{settings.app_name} API",
    version=settings.app_version,
    docs_url="/docs",
    lifespan=lifespan,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Basic hardening headers on every response; HSTS only in production over HTTPS."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if request.url.path.startswith("/api/auth"):
        response.headers["Cache-Control"] = "no-store"  # never cache tokens or account responses
    if settings.is_production and request.url.scheme == "https":
        # Tells browsers to use HTTPS for this site for the next year.
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


if settings.force_https:
    # Send plain-HTTP requests to HTTPS. Behind a reverse proxy on the same machine, uvicorn reads
    # X-Forwarded-Proto (it trusts 127.0.0.1 by default), so this still works. See deploy/Caddyfile.
    app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(images.router, prefix="/api")
app.include_router(copy.router, prefix="/api")
app.include_router(graphics.router, prefix="/api")
app.include_router(brand.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(demo.router, prefix="/api")
app.include_router(marketing.router, prefix="/api")
app.include_router(photo_assistant.router, prefix="/api")


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"message": f"{settings.app_name} API is running. See /docs."}
