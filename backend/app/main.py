import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import brand, copy, demo, export, graphics, health, history, images, marketing, photo_assistant
from app.core.config import get_settings
from app.core.errors import AppError
from app.services.storage_service import get_storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("zorvi")

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
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
