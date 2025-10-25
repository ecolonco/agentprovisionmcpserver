"""
Logging configuration using loguru
"""
import sys
from loguru import logger
from src.core.config import settings

# Remove default handler
logger.remove()

# Add custom handler with formatting
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.LOG_LEVEL,
    colorize=True,
)

# Add file handler for production
if settings.is_production:
    logger.add(
        "logs/mcp-server_{time}.log",
        rotation="500 MB",
        retention="10 days",
        level=settings.LOG_LEVEL,
        compression="zip",
    )

# Export logger
__all__ = ["logger"]
