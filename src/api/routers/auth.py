"""
Authentication API Endpoints

Complete authentication system with:
- User registration with email verification
- Login with JWT tokens
- Password reset flow
- Email confirmation
- Multi-tenant support
"""

from fastapi import APIRouter, Header, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import secrets

from src.db.session import get_db
from src.db.models import User, EmailVerificationToken, PasswordResetToken, UserRole
from src.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
)
from src.integrations.email_connector import GmailConnector
from src.utils.logger import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================
# Request/Response Models
# ============================================


class RegisterRequest(BaseModel):
    """User registration request"""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    full_name: str = Field(..., min_length=2, max_length=255, description="Full name")
    phone: Optional[str] = Field(None, max_length=50, description="Phone number")

    @validator("password")
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v

    class Config:
        schema_extra = {
            "example": {
                "email": "alumno@example.com",
                "password": "Secure123",
                "full_name": "Juan Pérez",
                "phone": "+56912345678",
            }
        }


class LoginRequest(BaseModel):
    """User login request"""

    email: EmailStr
    password: str

    class Config:
        schema_extra = {
            "example": {"email": "alumno@example.com", "password": "Secure123"}
        }


class LoginResponse(BaseModel):
    """User login response"""

    access_token: str
    token_type: str = "bearer"
    user: dict


class VerifyEmailRequest(BaseModel):
    """Email verification request"""

    token: str = Field(..., description="Verification token from email")


class ResendVerificationRequest(BaseModel):
    """Resend verification email request"""

    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    """Forgot password request"""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password request"""

    token: str = Field(..., description="Reset token from email")
    new_password: str = Field(..., min_length=8, description="New password")

    @validator("new_password")
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class ChangePasswordRequest(BaseModel):
    """Change password request (for authenticated users)"""

    current_password: str
    new_password: str = Field(..., min_length=8)

    @validator("new_password")
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserResponse(BaseModel):
    """User information response"""

    id: str
    email: str
    full_name: Optional[str]
    phone: Optional[str]
    is_verified: bool
    is_active: bool
    role: str
    tenant: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================
# Helper Functions
# ============================================


def generate_verification_token() -> str:
    """Generate a secure random verification token"""
    return secrets.token_urlsafe(32)


async def create_and_send_verification_email(
    user: User, db: AsyncSession, gmail: GmailConnector
):
    """Create verification token and send email"""
    # Create verification token
    token = generate_verification_token()
    expires_at = datetime.utcnow() + timedelta(hours=24)

    verification_token = EmailVerificationToken(
        user_id=user.id, token=token, expires_at=expires_at
    )
    db.add(verification_token)
    await db.commit()

    # Send verification email
    verification_link = f"https://talleresia.cl/verify-email?token={token}"

    try:
        await gmail.send_email(
            to_email=user.email,
            subject="Verifica tu cuenta - TalleresIA",
            html_content=f"""
            <h1>¡Bienvenido a TalleresIA!</h1>
            <p>Hola {user.full_name},</p>
            <p>Gracias por registrarte. Por favor verifica tu email haciendo clic en el siguiente enlace:</p>
            <p><a href="{verification_link}">Verificar mi cuenta</a></p>
            <p>Este enlace expira en 24 horas.</p>
            <p>Si no creaste esta cuenta, puedes ignorar este email.</p>
            """,
            text_content=f"""
            ¡Bienvenido a TalleresIA!

            Hola {user.full_name},

            Gracias por registrarte. Por favor verifica tu email visitando:
            {verification_link}

            Este enlace expira en 24 horas.
            """,
        )
    except Exception as e:
        logger.error(f"Failed to send verification email: {str(e)}")
        # Don't fail registration if email fails
        pass


async def create_and_send_password_reset_email(
    user: User, db: AsyncSession, gmail: GmailConnector
):
    """Create password reset token and send email"""
    # Create reset token
    token = generate_verification_token()
    expires_at = datetime.utcnow() + timedelta(hours=1)

    reset_token = PasswordResetToken(
        user_id=user.id, token=token, expires_at=expires_at
    )
    db.add(reset_token)
    await db.commit()

    # Send reset email
    reset_link = f"https://talleresia.cl/reset-password?token={token}"

    try:
        await gmail.send_email(
            to_email=user.email,
            subject="Recupera tu contraseña - TalleresIA",
            html_content=f"""
            <h1>Recuperación de Contraseña</h1>
            <p>Hola {user.full_name},</p>
            <p>Recibimos una solicitud para restablecer tu contraseña.</p>
            <p><a href="{reset_link}">Restablecer mi contraseña</a></p>
            <p>Este enlace expira en 1 hora.</p>
            <p>Si no solicitaste esto, puedes ignorar este email.</p>
            """,
            text_content=f"""
            Recuperación de Contraseña

            Hola {user.full_name},

            Recibimos una solicitud para restablecer tu contraseña.
            Visita este enlace: {reset_link}

            Este enlace expira en 1 hora.
            """,
        )
    except Exception as e:
        logger.error(f"Failed to send password reset email: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to send password reset email"
        )


async def get_current_user_from_token(
    authorization: str = Header(...), db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from Bearer token"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header"
        )

    token = authorization.replace("Bearer ", "")

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive"
            )

        return user

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
        )


# ============================================
# Authentication Endpoints
# ============================================


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    request: RegisterRequest,
    x_tenant: str = Header(..., alias="X-Tenant"),
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user

    **Multi-tenant**: Requires X-Tenant header (e.g., 'talleresia')

    Creates a new user account and sends verification email.
    User must verify email before being able to login.

    Example:
    ```bash
    curl -X POST https://mcp.tudominio.com/api/v1/auth/register \\
      -H "X-Tenant: talleresia" \\
      -H "Content-Type: application/json" \\
      -d '{
        "email": "alumno@example.com",
        "password": "Secure123",
        "full_name": "Juan Pérez"
      }'
    ```
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == request.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create new user
    hashed_password = get_password_hash(request.password)

    new_user = User(
        tenant=x_tenant,
        email=request.email,
        hashed_password=hashed_password,
        full_name=request.full_name,
        phone=request.phone,
        is_active=True,
        is_verified=False,
        role=UserRole.USER,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Send verification email
    try:
        gmail = GmailConnector(tenant=x_tenant)
        await create_and_send_verification_email(new_user, db, gmail)
    except Exception as e:
        logger.error(f"Failed to send verification email: {str(e)}")
        # Continue anyway - user can resend verification

    return {
        "message": "User registered successfully. Please check your email to verify your account.",
        "user_id": str(new_user.id),
        "email": new_user.email,
    }


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    x_tenant: str = Header(..., alias="X-Tenant"),
    db: AsyncSession = Depends(get_db),
):
    """
    Login user

    **Multi-tenant**: Requires X-Tenant header

    Returns JWT access token on successful authentication.
    User must have verified their email to login.

    Example:
    ```bash
    curl -X POST https://mcp.tudominio.com/api/v1/auth/login \\
      -H "X-Tenant: talleresia" \\
      -H "Content-Type: application/json" \\
      -d '{
        "email": "alumno@example.com",
        "password": "Secure123"
      }'
    ```
    """
    # Find user
    result = await db.execute(
        select(User).where(User.email == request.email, User.tenant == x_tenant)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Verify password
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled"
        )

    # Check if email is verified
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in",
        )

    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()

    # Create access token
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "tenant": user.tenant,
            "role": user.role.value,
        }
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "tenant": user.tenant,
            "is_verified": user.is_verified,
        },
    )


@router.post("/verify-email")
async def verify_email(
    request: VerifyEmailRequest, db: AsyncSession = Depends(get_db)
):
    """
    Verify user email with token

    User clicks link in verification email with token.

    Example:
    ```bash
    curl -X POST https://mcp.tudominio.com/api/v1/auth/verify-email \\
      -H "Content-Type: application/json" \\
      -d '{"token": "abc123..."}'
    ```
    """
    # Find token
    result = await db.execute(
        select(EmailVerificationToken).where(EmailVerificationToken.token == request.token)
    )
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token"
        )

    # Check if already used
    if token.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token has already been used",
        )

    # Check if expired
    if token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Token has expired"
        )

    # Get user
    result = await db.execute(select(User).where(User.id == token.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Mark user as verified
    user.is_verified = True
    token.used = True
    token.used_at = datetime.utcnow()

    await db.commit()

    return {
        "message": "Email verified successfully. You can now login.",
        "user_id": str(user.id),
        "email": user.email,
    }


@router.post("/resend-verification")
async def resend_verification(
    request: ResendVerificationRequest,
    x_tenant: str = Header(..., alias="X-Tenant"),
    db: AsyncSession = Depends(get_db),
):
    """
    Resend verification email

    If user didn't receive verification email or it expired.

    Example:
    ```bash
    curl -X POST https://mcp.tudominio.com/api/v1/auth/resend-verification \\
      -H "X-Tenant: talleresia" \\
      -H "Content-Type: application/json" \\
      -d '{"email": "alumno@example.com"}'
    ```
    """
    # Find user
    result = await db.execute(
        select(User).where(User.email == request.email, User.tenant == x_tenant)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Don't reveal if email exists
        return {"message": "If the email exists, a verification link has been sent."}

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already verified"
        )

    # Send new verification email
    gmail = GmailConnector(tenant=x_tenant)
    await create_and_send_verification_email(user, db, gmail)

    return {"message": "Verification email sent. Please check your inbox."}


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    x_tenant: str = Header(..., alias="X-Tenant"),
    db: AsyncSession = Depends(get_db),
):
    """
    Request password reset

    Sends password reset email with token.

    Example:
    ```bash
    curl -X POST https://mcp.tudominio.com/api/v1/auth/forgot-password \\
      -H "X-Tenant: talleresia" \\
      -H "Content-Type: application/json" \\
      -d '{"email": "alumno@example.com"}'
    ```
    """
    # Find user
    result = await db.execute(
        select(User).where(User.email == request.email, User.tenant == x_tenant)
    )
    user = result.scalar_one_or_none()

    if not user:
        # Don't reveal if email exists
        return {
            "message": "If the email exists, a password reset link has been sent."
        }

    # Send password reset email
    gmail = GmailConnector(tenant=x_tenant)
    await create_and_send_password_reset_email(user, db, gmail)

    return {"message": "Password reset email sent. Please check your inbox."}


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
):
    """
    Reset password with token

    User clicks link in password reset email with token.

    Example:
    ```bash
    curl -X POST https://mcp.tudominio.com/api/v1/auth/reset-password \\
      -H "Content-Type: application/json" \\
      -d '{
        "token": "xyz789...",
        "new_password": "NewSecure123"
      }'
    ```
    """
    # Find token
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == request.token)
    )
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token"
        )

    # Check if already used
    if token.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token has already been used",
        )

    # Check if expired
    if token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Token has expired"
        )

    # Get user
    result = await db.execute(select(User).where(User.id == token.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Update password
    user.hashed_password = get_password_hash(request.new_password)
    token.used = True
    token.used_at = datetime.utcnow()

    await db.commit()

    return {"message": "Password reset successfully. You can now login with your new password."}


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Change password (authenticated user)

    User must be logged in to change their password.

    Example:
    ```bash
    curl -X POST https://mcp.tudominio.com/api/v1/auth/change-password \\
      -H "Authorization: Bearer eyJ..." \\
      -H "Content-Type: application/json" \\
      -d '{
        "current_password": "OldPassword123",
        "new_password": "NewPassword123"
      }'
    ```
    """
    user = await get_current_user_from_token(authorization, db)

    # Verify current password
    if not verify_password(request.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    user.hashed_password = get_password_hash(request.new_password)
    await db.commit()

    return {"message": "Password changed successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    authorization: str = Header(...), db: AsyncSession = Depends(get_db)
):
    """
    Get current user information

    Returns information about the authenticated user.

    Example:
    ```bash
    curl https://mcp.tudominio.com/api/v1/auth/me \\
      -H "Authorization: Bearer eyJ..."
    ```
    """
    user = await get_current_user_from_token(authorization, db)

    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        is_verified=user.is_verified,
        is_active=user.is_active,
        role=user.role.value,
        tenant=user.tenant,
        created_at=user.created_at,
    )
