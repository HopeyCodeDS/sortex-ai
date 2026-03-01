from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os

from .routes import auth, documents, extractions, validations, reviews, exports
from .routes import health as health_router
from ..infrastructure.monitoring.logging import get_logger

logger = get_logger("sortex.api")

app = FastAPI(
    title="Sortex AI API",
    description="Intelligent Transport Document Processing Platform",
    version="1.0.0"
)

# CORS configuration
cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
    max_age=600,
)

# Include routers
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(documents.router, prefix="/api/v1", tags=["documents"])
app.include_router(extractions.router, prefix="/api/v1", tags=["extractions"])
app.include_router(validations.router, prefix="/api/v1", tags=["validations"])
app.include_router(reviews.router, prefix="/api/v1", tags=["reviews"])
app.include_router(exports.router, prefix="/api/v1", tags=["exports"])


@app.get("/")
async def root():
    return {"message": "Sortex AI API", "version": "1.0.0"}


app.include_router(health_router.router, tags=["health"])


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(
        "Unhandled exception",
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        path=request.url.path,
        method=request.method
    )
    return JSONResponse(
        status_code=500,
        content={"error": {"message": str(exc), "type": type(exc).__name__}}
    )

