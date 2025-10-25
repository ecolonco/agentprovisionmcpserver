"""
Stripe Payment Integration Connector
Handles payment processing for TalleresIA and other applications
"""
import httpx
from typing import Dict, Any, Optional
from src.utils.logger import logger


class StripeConnector:
    """
    Connector for Stripe Payment API
    Processes payments, creates customers, handles webhooks
    """

    def __init__(self, api_key: str, tenant: str = "default"):
        """
        Initialize Stripe connector

        Args:
            api_key: Stripe secret key (sk_live_xxx or sk_test_xxx)
            tenant: Tenant identifier (e.g., "talleresia", "eunacom")
        """
        self.api_key = api_key
        self.tenant = tenant
        self.base_url = "https://api.stripe.com/v1"
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"StripeConnector initialized for tenant: {tenant}")

    async def create_payment_intent(
        self,
        amount: int,
        currency: str = "usd",
        customer_email: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Create a payment intent

        Args:
            amount: Amount in cents (e.g., 5000 = $50.00)
            currency: Currency code (usd, clp, etc.)
            customer_email: Customer email
            metadata: Additional data to attach

        Returns:
            Payment intent object
        """
        logger.info(
            f"Creating payment intent for {self.tenant}: "
            f"amount={amount}, currency={currency}"
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "amount": amount,
            "currency": currency,
        }

        if customer_email:
            data["receipt_email"] = customer_email

        if metadata:
            # Add tenant to metadata
            metadata["tenant"] = self.tenant
            for key, value in metadata.items():
                data[f"metadata[{key}]"] = value

        try:
            response = await self.client.post(
                f"{self.base_url}/payment_intents",
                headers=headers,
                data=data
            )
            response.raise_for_status()
            result = response.json()

            logger.info(f"Payment intent created: {result['id']}")
            return result

        except httpx.HTTPError as e:
            logger.error(f"Stripe API error: {str(e)}")
            raise

    async def retrieve_payment_intent(self, payment_intent_id: str) -> Dict[str, Any]:
        """
        Retrieve payment intent details

        Args:
            payment_intent_id: Payment intent ID (pi_xxx)

        Returns:
            Payment intent object
        """
        logger.info(f"Retrieving payment intent: {payment_intent_id}")

        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        try:
            response = await self.client.get(
                f"{self.base_url}/payment_intents/{payment_intent_id}",
                headers=headers
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error retrieving payment intent: {str(e)}")
            raise

    async def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe customer

        Args:
            email: Customer email
            name: Customer name
            metadata: Additional metadata

        Returns:
            Customer object
        """
        logger.info(f"Creating Stripe customer: {email}")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {"email": email}

        if name:
            data["name"] = name

        if metadata:
            metadata["tenant"] = self.tenant
            for key, value in metadata.items():
                data[f"metadata[{key}]"] = value

        try:
            response = await self.client.post(
                f"{self.base_url}/customers",
                headers=headers,
                data=data
            )
            response.raise_for_status()
            result = response.json()

            logger.info(f"Customer created: {result['id']}")
            return result

        except httpx.HTTPError as e:
            logger.error(f"Error creating customer: {str(e)}")
            raise

    async def process_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Stripe webhook events

        Args:
            payload: Webhook payload from Stripe

        Returns:
            Processing result
        """
        event_type = payload.get("type")
        logger.info(f"Processing Stripe webhook: {event_type}")

        if event_type == "payment_intent.succeeded":
            payment_intent = payload["data"]["object"]
            logger.info(f"Payment succeeded: {payment_intent['id']}")

            return {
                "status": "success",
                "payment_id": payment_intent["id"],
                "amount": payment_intent["amount"],
                "customer_email": payment_intent.get("receipt_email")
            }

        elif event_type == "payment_intent.payment_failed":
            payment_intent = payload["data"]["object"]
            logger.warning(f"Payment failed: {payment_intent['id']}")

            return {
                "status": "failed",
                "payment_id": payment_intent["id"],
                "error": payment_intent.get("last_payment_error")
            }

        else:
            logger.info(f"Unhandled webhook event: {event_type}")
            return {
                "status": "unhandled",
                "event_type": event_type
            }

    async def refund_payment(
        self,
        payment_intent_id: str,
        amount: Optional[int] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refund a payment

        Args:
            payment_intent_id: Payment intent to refund
            amount: Amount to refund (None = full refund)
            reason: Reason for refund

        Returns:
            Refund object
        """
        logger.info(f"Processing refund for: {payment_intent_id}")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {"payment_intent": payment_intent_id}

        if amount:
            data["amount"] = amount
        if reason:
            data["reason"] = reason

        try:
            response = await self.client.post(
                f"{self.base_url}/refunds",
                headers=headers,
                data=data
            )
            response.raise_for_status()
            result = response.json()

            logger.info(f"Refund created: {result['id']}")
            return result

        except httpx.HTTPError as e:
            logger.error(f"Error creating refund: {str(e)}")
            raise

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# ============================================
# Helper Functions
# ============================================

async def get_stripe_connector(tenant: str) -> StripeConnector:
    """
    Factory function to get Stripe connector for specific tenant

    Args:
        tenant: Tenant identifier

    Returns:
        Configured StripeConnector instance
    """
    # In production, load from database or config
    # For now, use environment variables

    from src.core.config import settings
    import os

    # Get tenant-specific Stripe key
    stripe_key = os.getenv(f"STRIPE_SECRET_KEY_{tenant.upper()}")

    if not stripe_key:
        # Fallback to default key
        stripe_key = os.getenv("STRIPE_SECRET_KEY")

    if not stripe_key:
        raise ValueError(f"No Stripe API key found for tenant: {tenant}")

    return StripeConnector(api_key=stripe_key, tenant=tenant)
