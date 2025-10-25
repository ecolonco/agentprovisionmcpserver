"""
Payment Processing Endpoints
Handles payment operations through various providers (Stripe, Transbank, etc.)
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db import crud, schemas, models
from src.core.security import get_current_user
from src.integrations.stripe_connector import get_stripe_connector
from src.utils.logger import logger

router = APIRouter()


# ============================================
# Request/Response Models
# ============================================

class PaymentIntentRequest(BaseModel):
    """Request to create a payment intent"""
    amount: int  # Amount in cents
    currency: str = "usd"
    customer_email: EmailStr
    customer_name: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[dict] = {}


class PaymentIntentResponse(BaseModel):
    """Response with payment intent details"""
    payment_intent_id: str
    client_secret: str
    amount: int
    currency: str
    status: str


class WebhookEvent(BaseModel):
    """Stripe webhook event"""
    type: str
    data: dict


# ============================================
# Endpoints
# ============================================

@router.post(
    "/payments/create-intent",
    response_model=PaymentIntentResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_payment_intent(
    request: PaymentIntentRequest,
    x_tenant: str = Header(..., description="Tenant identifier (e.g., talleresia, eunacom)"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a payment intent with Stripe

    This endpoint creates a payment intent that can be used by your frontend
    to collect payment information.

    **Example for TalleresIA:**
    ```json
    POST /api/v1/payments/create-intent
    Headers:
      X-API-Key: your-api-key
      X-Tenant: talleresia
    Body:
    {
      "amount": 5000,
      "currency": "usd",
      "customer_email": "alumno@example.com",
      "customer_name": "Juan Pérez",
      "description": "Taller de IA Básico",
      "metadata": {
        "taller_id": "taller-ia-basico-2024",
        "enrollment_id": "enr_12345"
      }
    }
    ```
    """
    logger.info(
        f"Creating payment intent for tenant {x_tenant}: "
        f"amount={request.amount}, email={request.customer_email}"
    )

    try:
        # Get Stripe connector for this tenant
        stripe = await get_stripe_connector(x_tenant)

        # Add description and customer name to metadata
        metadata = request.metadata or {}
        metadata.update({
            "description": request.description,
            "customer_name": request.customer_name,
            "api_user": current_user.get("name", "unknown")
        })

        # Create payment intent
        payment_intent = await stripe.create_payment_intent(
            amount=request.amount,
            currency=request.currency,
            customer_email=request.customer_email,
            metadata=metadata
        )

        # Create audit log
        await crud.AuditLogCRUD.create(
            db,
            schemas.AuditLogCreate(
                event_type="payment_intent_created",
                action="CREATE",
                status="SUCCESS",
                entity_type=models.EntityType.PAYMENT,
                entity_id=payment_intent["id"],
                source_system=models.IntegrationSystem.DENTALERP,  # Your system
                target_system=models.IntegrationSystem.BANK,  # Stripe
                request_data={
                    "amount": request.amount,
                    "currency": request.currency,
                    "email": request.customer_email
                },
                response_data=payment_intent
            )
        )

        await stripe.close()

        return PaymentIntentResponse(
            payment_intent_id=payment_intent["id"],
            client_secret=payment_intent["client_secret"],
            amount=payment_intent["amount"],
            currency=payment_intent["currency"],
            status=payment_intent["status"]
        )

    except Exception as e:
        logger.error(f"Error creating payment intent: {str(e)}")

        # Log error
        await crud.AuditLogCRUD.create(
            db,
            schemas.AuditLogCreate(
                event_type="payment_intent_failed",
                action="CREATE",
                status="FAILED",
                entity_type=models.EntityType.PAYMENT,
                error_details={"error": str(e)}
            )
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating payment intent: {str(e)}"
        )


@router.post("/payments/webhook")
async def stripe_webhook(
    event: WebhookEvent,
    x_tenant: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Stripe webhook events

    Configure this URL in your Stripe dashboard:
    https://your-mcp-server.com/api/v1/payments/webhook

    **Events handled:**
    - payment_intent.succeeded
    - payment_intent.payment_failed
    - charge.refunded
    """
    logger.info(f"Received Stripe webhook: {event.type}")

    try:
        stripe = await get_stripe_connector(x_tenant)

        # Process webhook
        result = await stripe.process_webhook(event.dict())

        # Log webhook
        await crud.AuditLogCRUD.create(
            db,
            schemas.AuditLogCreate(
                event_type=f"webhook_{event.type}",
                action="WEBHOOK",
                status="SUCCESS" if result.get("status") == "success" else "INFO",
                entity_type=models.EntityType.PAYMENT,
                entity_id=result.get("payment_id"),
                request_data=event.dict(),
                response_data=result
            )
        )

        await stripe.close()

        return {"status": "received", "result": result}

    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing webhook: {str(e)}"
        )


@router.get("/payments/{payment_intent_id}")
async def get_payment_status(
    payment_intent_id: str,
    x_tenant: str = Header(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Get payment intent status

    Use this to check if a payment was successful
    """
    logger.info(f"Getting payment status: {payment_intent_id}")

    try:
        stripe = await get_stripe_connector(x_tenant)
        payment_intent = await stripe.retrieve_payment_intent(payment_intent_id)
        await stripe.close()

        return {
            "id": payment_intent["id"],
            "status": payment_intent["status"],
            "amount": payment_intent["amount"],
            "currency": payment_intent["currency"],
            "payment_method": payment_intent.get("payment_method")
        }

    except Exception as e:
        logger.error(f"Error retrieving payment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment not found: {str(e)}"
        )


@router.post("/payments/{payment_intent_id}/refund")
async def refund_payment(
    payment_intent_id: str,
    amount: Optional[int] = None,
    reason: Optional[str] = None,
    x_tenant: str = Header(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Refund a payment

    **Parameters:**
    - amount: Amount to refund in cents (None = full refund)
    - reason: Reason for refund (optional)
    """
    logger.info(f"Processing refund for: {payment_intent_id}")

    try:
        stripe = await get_stripe_connector(x_tenant)
        refund = await stripe.refund_payment(
            payment_intent_id=payment_intent_id,
            amount=amount,
            reason=reason
        )

        # Log refund
        await crud.AuditLogCRUD.create(
            db,
            schemas.AuditLogCreate(
                event_type="payment_refunded",
                action="UPDATE",
                status="SUCCESS",
                entity_type=models.EntityType.PAYMENT,
                entity_id=payment_intent_id,
                request_data={
                    "amount": amount,
                    "reason": reason,
                    "user": current_user.get("name")
                },
                response_data=refund
            )
        )

        await stripe.close()

        return {
            "refund_id": refund["id"],
            "amount": refund["amount"],
            "status": refund["status"]
        }

    except Exception as e:
        logger.error(f"Error processing refund: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing refund: {str(e)}"
        )
