"""
Email API Endpoints

Provides REST API for sending emails via Gmail SMTP.
All endpoints require authentication via X-API-Key header.
Multi-tenant support via X-Tenant header.
"""

from fastapi import APIRouter, Header, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from src.integrations.email_connector import GmailConnector, EmailTemplates
from src.db.session import get_db
from src.db.models import AuditLog
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/emails", tags=["Emails"])
logger = logging.getLogger(__name__)


# ============================================
# Request/Response Models
# ============================================


class SendEmailRequest(BaseModel):
    """Request to send a custom email"""

    to_email: EmailStr = Field(..., description="Recipient email address")
    subject: str = Field(..., min_length=1, max_length=200, description="Email subject")
    html_content: str = Field(..., description="HTML content of the email")
    text_content: Optional[str] = Field(None, description="Plain text fallback")
    cc: Optional[List[EmailStr]] = Field(None, description="CC recipients")
    bcc: Optional[List[EmailStr]] = Field(None, description="BCC recipients")
    reply_to: Optional[EmailStr] = Field(None, description="Reply-To address")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    class Config:
        schema_extra = {
            "example": {
                "to_email": "alumno@example.com",
                "subject": "Bienvenido a TalleresIA",
                "html_content": "<h1>Hola!</h1><p>Gracias por inscribirte.</p>",
                "text_content": "Hola! Gracias por inscribirte.",
            }
        }


class SendTemplateEmailRequest(BaseModel):
    """Request to send email using a template"""

    to_email: EmailStr = Field(..., description="Recipient email address")
    template_name: str = Field(
        ..., description="Template name (e.g., 'payment_confirmation')"
    )
    context: Dict[str, Any] = Field(..., description="Template variables")
    subject: Optional[str] = Field(None, description="Override template subject")
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None
    reply_to: Optional[EmailStr] = None
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        schema_extra = {
            "example": {
                "to_email": "alumno@example.com",
                "template_name": "payment_confirmation",
                "context": {
                    "customer_name": "Juan Pérez",
                    "amount": 50000,
                    "currency": "CLP",
                    "description": "Taller IA Básico",
                    "payment_date": "2024-01-15",
                },
            }
        }


class SendPaymentConfirmationRequest(BaseModel):
    """Quick send payment confirmation email"""

    to_email: EmailStr
    customer_name: str
    amount: int
    currency: str = "CLP"
    description: str
    payment_date: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "to_email": "alumno@example.com",
                "customer_name": "Juan Pérez",
                "amount": 50000,
                "currency": "CLP",
                "description": "Taller IA Básico 2024",
            }
        }


class EmailResponse(BaseModel):
    """Email sending response"""

    status: str
    message_id: str
    to: str
    subject: str
    sent_at: str
    tenant: str


# ============================================
# Dependency: Get Gmail Connector
# ============================================


async def get_gmail_connector(x_tenant: str = Header(..., alias="X-Tenant")) -> GmailConnector:
    """Get Gmail connector for the specified tenant"""
    try:
        return GmailConnector(tenant=x_tenant)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Gmail not configured for tenant '{x_tenant}': {str(e)}",
        )


# ============================================
# Email Endpoints
# ============================================


@router.post("/send", response_model=EmailResponse)
async def send_email(
    request: SendEmailRequest,
    gmail: GmailConnector = Depends(get_gmail_connector),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a custom email via Gmail SMTP

    **Authentication**: Requires X-API-Key header
    **Multi-tenant**: Requires X-Tenant header (e.g., 'talleresia')

    Example:
    ```bash
    curl -X POST https://mcp.tudominio.com/api/v1/emails/send \\
      -H "X-API-Key: mcp_talleresia_abc123" \\
      -H "X-Tenant: talleresia" \\
      -H "Content-Type: application/json" \\
      -d '{
        "to_email": "alumno@example.com",
        "subject": "Bienvenido",
        "html_content": "<h1>Hola!</h1>"
      }'
    ```
    """
    try:
        result = await gmail.send_email(
            to_email=request.to_email,
            subject=request.subject,
            html_content=request.html_content,
            text_content=request.text_content,
            cc=request.cc,
            bcc=request.bcc,
            reply_to=request.reply_to,
        )

        # Log to audit trail
        audit_log = AuditLog(
            event_type="email_sent",
            action="SEND",
            status="SUCCESS",
            entity_type=None,  # emails are not entity types
            entity_id=result["message_id"],
            request_data={
                "to": request.to_email,
                "subject": request.subject,
                "tenant": gmail.tenant,
                "metadata": request.metadata,
            },
            response_data=result,
        )
        db.add(audit_log)
        await db.commit()

        return EmailResponse(**result)

    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


@router.post("/send-template", response_model=EmailResponse)
async def send_template_email(
    request: SendTemplateEmailRequest,
    gmail: GmailConnector = Depends(get_gmail_connector),
    db: AsyncSession = Depends(get_db),
):
    """
    Send email using a pre-defined template

    **Templates available**:
    - `payment_confirmation` - Payment confirmation email
    - `subscription_activated` - Subscription activation email
    - Custom templates in `src/templates/emails/`

    Example:
    ```bash
    curl -X POST https://mcp.tudominio.com/api/v1/emails/send-template \\
      -H "X-API-Key: mcp_talleresia_abc123" \\
      -H "X-Tenant: talleresia" \\
      -H "Content-Type: application/json" \\
      -d '{
        "to_email": "alumno@example.com",
        "template_name": "payment_confirmation",
        "context": {
          "customer_name": "Juan",
          "amount": 50000,
          "currency": "CLP",
          "description": "Taller IA",
          "payment_date": "2024-01-15"
        }
      }'
    ```
    """
    try:
        result = await gmail.send_template_email(
            to_email=request.to_email,
            template_name=request.template_name,
            context=request.context,
            subject=request.subject,
            cc=request.cc,
            bcc=request.bcc,
            reply_to=request.reply_to,
        )

        # Log to audit trail
        audit_log = AuditLog(
            event_type="email_sent",
            action="SEND",
            status="SUCCESS",
            entity_type=None,
            entity_id=result["message_id"],
            request_data={
                "to": request.to_email,
                "template": request.template_name,
                "tenant": gmail.tenant,
                "metadata": request.metadata,
            },
            response_data=result,
        )
        db.add(audit_log)
        await db.commit()

        return EmailResponse(**result)

    except Exception as e:
        logger.error(f"Failed to send template email: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to send template email: {str(e)}"
        )


@router.post("/send-payment-confirmation", response_model=EmailResponse)
async def send_payment_confirmation(
    request: SendPaymentConfirmationRequest,
    gmail: GmailConnector = Depends(get_gmail_connector),
    db: AsyncSession = Depends(get_db),
):
    """
    Quick endpoint to send payment confirmation email

    Uses the built-in payment confirmation template.

    Example:
    ```bash
    curl -X POST https://mcp.tudominio.com/api/v1/emails/send-payment-confirmation \\
      -H "X-API-Key: mcp_talleresia_abc123" \\
      -H "X-Tenant: talleresia" \\
      -H "Content-Type: application/json" \\
      -d '{
        "to_email": "alumno@example.com",
        "customer_name": "Juan Pérez",
        "amount": 50000,
        "currency": "CLP",
        "description": "Taller IA Básico 2024"
      }'
    ```
    """
    try:
        payment_date = request.payment_date or datetime.now().strftime("%Y-%m-%d")

        template = EmailTemplates.payment_confirmation(
            customer_name=request.customer_name,
            amount=request.amount,
            currency=request.currency,
            description=request.description,
            payment_date=payment_date,
        )

        result = await gmail.send_email(
            to_email=request.to_email,
            subject=template["subject"],
            html_content=template["html"],
            text_content=template["text"],
        )

        # Log to audit trail
        audit_log = AuditLog(
            event_type="email_sent",
            action="SEND",
            status="SUCCESS",
            entity_type=None,
            entity_id=result["message_id"],
            request_data={
                "to": request.to_email,
                "type": "payment_confirmation",
                "amount": request.amount,
                "currency": request.currency,
                "tenant": gmail.tenant,
            },
            response_data=result,
        )
        db.add(audit_log)
        await db.commit()

        return EmailResponse(**result)

    except Exception as e:
        logger.error(f"Failed to send payment confirmation: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to send payment confirmation: {str(e)}"
        )


@router.get("/test")
async def test_gmail_connection(
    gmail: GmailConnector = Depends(get_gmail_connector),
):
    """
    Test Gmail SMTP connection for the tenant

    Returns configuration status (without exposing credentials)
    """
    return {
        "status": "configured",
        "tenant": gmail.tenant,
        "smtp_host": gmail.smtp_host,
        "smtp_port": gmail.smtp_port,
        "from_email": gmail.from_email,
        "from_name": gmail.from_name,
        "smtp_user_configured": bool(gmail.smtp_user),
        "smtp_password_configured": bool(gmail.smtp_password),
    }
