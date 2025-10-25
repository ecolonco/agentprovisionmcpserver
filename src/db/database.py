"""
Database connection and session management
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

from src.core.config import settings
from src.db.models import Base

# ============================================
# Async Database Engine
# ============================================

# Create async engine for production use
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verify connections before using
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ============================================
# Sync Database Engine (for Alembic migrations)
# ============================================

# Convert async URL to sync for Alembic
sync_database_url = settings.DATABASE_URL.replace(
    "postgresql+asyncpg://",
    "postgresql+psycopg2://"
)

sync_engine = create_engine(
    sync_database_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)


# ============================================
# Database Session Dependency
# ============================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions
    Yields an async database session and closes it after use

    Usage:
        @app.get("/items/")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ============================================
# Database Initialization
# ============================================

async def init_db() -> None:
    """
    Initialize database tables
    Creates all tables defined in models
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db() -> None:
    """
    Drop all database tables
    WARNING: This will delete all data!
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def check_db_connection() -> bool:
    """
    Check if database connection is working

    Returns:
        True if connection successful, False otherwise
    """
    try:
        async with async_engine.connect() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


# ============================================
# Database Health Check
# ============================================

async def get_db_health() -> dict:
    """
    Get database health status

    Returns:
        Dictionary with health information
    """
    try:
        async with async_engine.connect() as conn:
            result = await conn.execute("SELECT version()")
            version = result.scalar()

            return {
                "status": "healthy",
                "type": "postgresql",
                "version": version,
                "pool_size": async_engine.pool.size(),
                "checked_in_connections": async_engine.pool.checkedin(),
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }
