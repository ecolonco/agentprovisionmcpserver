"""
Health check endpoints
"""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db, get_db_health
from src.db import schemas
from src.core.config import settings

router = APIRouter()


@router.get("/health", response_model=schemas.HealthCheckResponse)
async def health_check():
    """
    Basic health check endpoint
    Returns service status and version
    """
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow(),
        "services": {
            "api": "running",
            "environment": settings.ENVIRONMENT,
        }
    }


@router.get("/health/detailed", response_model=schemas.HealthCheckDetail)
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """
    Detailed health check endpoint
    Checks all service dependencies
    """
    # Check database
    db_health = await get_db_health()

    # Check Redis (basic check)
    redis_health = {"status": "not_configured"}
    try:
        # TODO: Add Redis health check when implemented
        pass
    except Exception as e:
        redis_health = {"status": "unhealthy", "error": str(e)}

    # Check Kafka (optional)
    kafka_health = None
    # TODO: Add Kafka health check when implemented

    # Check Temporal (optional)
    temporal_health = None
    # TODO: Add Temporal health check when implemented

    return {
        "database": db_health,
        "redis": redis_health,
        "kafka": kafka_health,
        "temporal": temporal_health,
    }


@router.get("/ping")
async def ping():
    """
    Simple ping endpoint
    """
    return {"message": "pong"}
