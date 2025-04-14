import signal
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from backend.auth.router import router as auth_router
from backend.chat.router import router as chat_router
from backend.config import app_configs, settings
from backend.logger import logger
from backend.vector_db.router import router as vector_db_router

logger.info("Starting application")


# Redis connection verification
async def verify_redis_connection(redis_url: str) -> bool:
    try:
        redis_client = redis.from_url(url=redis_url)
        redis_client.ping()
        logger.info("Redis connection successful")
        redis_client.close()
        return True
    except Exception as e:
        logger.error(f"Redis connection failed: {str(e)}")
        return False


# Graceful shutdown handler
def handle_shutdown(signum, frame):
    logger.info("Received shutdown signal")
    raise SystemExit(0)


signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

redis_client = redis.StrictRedis(
    host=settings.REDIS_HOST or "localhost",
    port=settings.REDIS_PORT or 6379,
    decode_responses=True,
)


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncGenerator:
    # Startup
    try:
        yield
    except Exception as e:
        logger.error(f"Lifespan error: {str(e)}")
    finally:
        logger.info("Lifespan cleanup completed")


# Initialize FastAPI app
app = FastAPI(**app_configs, lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=settings.CORS_HEADERS,
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error: {str(exc)}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Health check endpoint
@app.get("/health", include_in_schema=False)
async def healthcheck() -> dict[str, str]:
    logger.info("Healthcheck")
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "project_name": settings.PROJECT_NAME,
    }


# Include routers
app.include_router(auth_router, tags=["Auth"], prefix="/auth")
app.include_router(chat_router, tags=["Chat"], prefix="/chatbot")
app.include_router(vector_db_router, tags=["Vector DB"], prefix="/qdrant")

if __name__ == "__main__":
    import uvicorn

    config = uvicorn.Config(
        "backend.main:app",
        host=settings.SITE_DOMAIN,
        port=8000,
        log_level="info",
        reload=settings.DEBUG,
    )

    server = uvicorn.Server(config)
    server.run()
