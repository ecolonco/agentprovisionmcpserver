"""
Security utilities for authentication and authorization
Handles JWT tokens and API key validation
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader

from src.core.config import settings

# ============================================
# Password Hashing
# ============================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


# ============================================
# JWT Token Management
# ============================================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token

    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        # Validate token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ============================================
# API Key Validation
# ============================================

# Define API key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Store valid API keys (in production, this should be in database)
# Format: {api_key: {system_name, permissions, etc.}}
VALID_API_KEYS: Dict[str, Dict[str, Any]] = {
    # Example API keys - should be loaded from database
    "test-api-key-adp": {
        "system": "adp",
        "name": "ADP Integration",
        "permissions": ["read", "write"]
    },
    "test-api-key-eaglesoft": {
        "system": "eaglesoft",
        "name": "Eaglesoft Integration",
        "permissions": ["read", "write"]
    },
    # Add more API keys as needed
}


async def validate_api_key(
    api_key: Optional[str] = Security(api_key_header)
) -> Dict[str, Any]:
    """
    Validate API key from request header

    Args:
        api_key: API key from X-API-Key header

    Returns:
        API key metadata (system, name, permissions)

    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Check if API key is valid
    key_data = VALID_API_KEYS.get(api_key)

    if not key_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return key_data


# ============================================
# Bearer Token Validation
# ============================================

security = HTTPBearer()


async def validate_bearer_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict[str, Any]:
    """
    Validate Bearer token from Authorization header

    Args:
        credentials: HTTP authorization credentials

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid
    """
    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme"
        )

    token = credentials.credentials
    return decode_access_token(token)


# ============================================
# Combined Authentication
# ============================================

async def get_current_user(
    api_key: Optional[str] = Security(api_key_header),
    bearer_credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Dict[str, Any]:
    """
    Flexible authentication that accepts either API key or Bearer token

    Args:
        api_key: Optional API key from header
        bearer_credentials: Optional Bearer token credentials

    Returns:
        User/system information

    Raises:
        HTTPException: If neither valid API key nor token is provided
    """
    # Try API key first
    if api_key and api_key in VALID_API_KEYS:
        return {
            "auth_type": "api_key",
            "system": VALID_API_KEYS[api_key]["system"],
            "name": VALID_API_KEYS[api_key]["name"],
            "permissions": VALID_API_KEYS[api_key]["permissions"],
        }

    # Try Bearer token
    if bearer_credentials:
        try:
            payload = decode_access_token(bearer_credentials.credentials)
            return {
                "auth_type": "bearer_token",
                "user_id": payload.get("sub"),
                "permissions": payload.get("permissions", []),
            }
        except HTTPException:
            pass

    # No valid authentication found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Provide either X-API-Key or Bearer token.",
        headers={"WWW-Authenticate": "Bearer, ApiKey"},
    )


# ============================================
# Permission Checking
# ============================================

def check_permission(
    user: Dict[str, Any],
    required_permission: str
) -> bool:
    """
    Check if user/system has a specific permission

    Args:
        user: User/system data from authentication
        required_permission: Permission to check

    Returns:
        True if user has permission, False otherwise
    """
    permissions = user.get("permissions", [])
    return required_permission in permissions or "admin" in permissions


def require_permission(required_permission: str):
    """
    Decorator to require a specific permission

    Args:
        required_permission: Permission required to access the endpoint

    Returns:
        Dependency function for FastAPI
    """
    async def permission_checker(
        user: Dict[str, Any] = Security(get_current_user)
    ) -> Dict[str, Any]:
        if not check_permission(user, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required permission: {required_permission}"
            )
        return user

    return permission_checker


# ============================================
# Rate Limiting
# ============================================

class RateLimiter:
    """
    Simple in-memory rate limiter
    In production, use Redis-based rate limiting
    """

    def __init__(self):
        self.requests: Dict[str, list] = {}

    def is_allowed(
        self,
        key: str,
        max_requests: int = settings.RATE_LIMIT_PER_MINUTE,
        window_seconds: int = 60
    ) -> bool:
        """
        Check if request is allowed under rate limit

        Args:
            key: Unique identifier (IP, user ID, API key)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            True if allowed, False if rate limit exceeded
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)

        # Get or create request list for this key
        if key not in self.requests:
            self.requests[key] = []

        # Remove old requests outside the window
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if req_time > cutoff
        ]

        # Check if under limit
        if len(self.requests[key]) >= max_requests:
            return False

        # Add current request
        self.requests[key].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


# ============================================
# Utility Functions
# ============================================

def generate_api_key() -> str:
    """
    Generate a secure random API key

    Returns:
        Random API key string
    """
    import secrets
    return f"mcp_{secrets.token_urlsafe(32)}"


def create_service_token(
    service_name: str,
    permissions: list,
    expires_days: int = 365
) -> str:
    """
    Create a long-lived service token for integration

    Args:
        service_name: Name of the service
        permissions: List of permissions to grant
        expires_days: Number of days until expiration

    Returns:
        JWT service token
    """
    data = {
        "sub": f"service:{service_name}",
        "type": "service",
        "permissions": permissions,
    }

    expires_delta = timedelta(days=expires_days)
    return create_access_token(data, expires_delta)
