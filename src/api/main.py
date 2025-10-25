"""
FastAPI Application - Main Entry Point
MCP Server for AgentProvision
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from src.core.config import settings
from src.db.database import init_db, check_db_connection
from src.api.routers import health, mappings, sync, payments, emails, auth
from src.utils.logger import logger


# ============================================
# Lifespan Context Manager
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("🚀 Starting MCP Server...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Version: {settings.APP_VERSION}")

    # Check database connection
    logger.info("Checking database connection...")
    db_connected = await check_db_connection()

    if not db_connected:
        logger.error("❌ Failed to connect to database")
    else:
        logger.info("✅ Database connection successful")

        # Initialize database tables
        if settings.is_development:
            logger.info("Initializing database tables...")
            await init_db()
            logger.info("✅ Database tables initialized")

    logger.info("✅ MCP Server started successfully")

    yield

    # Shutdown
    logger.info("🛑 Shutting down MCP Server...")
    logger.info("✅ MCP Server shutdown complete")


# ============================================
# FastAPI Application
# ============================================

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Mapping & Control Plane Server for AgentProvision - AI orchestration backbone for DataFlow AI",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# ============================================
# Middleware
# ============================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests"""
    logger.info(f"📥 {request.method} {request.url.path}")

    try:
        response = await call_next(request)
        logger.info(f"📤 {request.method} {request.url.path} - {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"❌ {request.method} {request.url.path} - Error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error", "detail": str(e)}
        )


# ============================================
# Exception Handlers
# ============================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred"
        }
    )


# ============================================
# Routers
# ============================================

# Include health check router (no prefix, no auth required)
app.include_router(
    health.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Health"]
)

# Include mappings router
app.include_router(
    mappings.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Mappings"]
)

# Include sync/workflow router
app.include_router(
    sync.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Sync & Workflows"]
)

# Include payments router
app.include_router(
    payments.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Payments"]
)

# Include emails router
app.include_router(
    emails.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Emails"]
)

# Include auth router
app.include_router(
    auth.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Authentication"]
)

# ============================================
# Prometheus Metrics
# ============================================

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# ============================================
# Root Endpoint
# ============================================

@app.get("/")
async def root():
    """
    Root endpoint - API information
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs" if settings.DEBUG else "Documentation disabled in production",
        "health": f"{settings.API_V1_PREFIX}/health",
        "metrics": "/metrics"
    }


# ============================================
# Main Entry Point (for development)
# ============================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
