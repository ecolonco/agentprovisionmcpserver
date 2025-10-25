"""
Flow.cl Payment Integration Connector (Chile)
Handles payment processing for Chilean market through Flow.cl

Flow.cl supports:
- Webpay (credit/debit cards)
- Bank transfers
- Servipag
- Multicaja
- Onepay

Documentation: https://www.flow.cl/docs/api.html
"""
import httpx
import hmac
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime
from src.utils.logger import logger


class FlowConnector:
    """
    Connector for Flow.cl Payment API (Chile)

    Flow.cl is the leading payment gateway in Chile, supporting
    multiple local payment methods.
    """

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        tenant: str = "default",
        sandbox: bool = False
    ):
        """
        Initialize Flow connector

        Args:
            api_key: Flow API Key
            secret_key: Flow Secret Key (for signature)
            tenant: Tenant identifier
            sandbox: Use sandbox environment (default: False)
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.tenant = tenant
        self.sandbox = sandbox

        # Flow endpoints
        if sandbox:
            self.base_url = "https://sandbox.flow.cl/api"
            self.payment_url = "https://sandbox.flow.cl/app/web/pay.php"
        else:
            self.base_url = "https://www.flow.cl/api"
            self.payment_url = "https://www.flow.cl/app/web/pay.php"

        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info(f"FlowConnector initialized for tenant: {tenant} (sandbox={sandbox})")

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """
        Generate Flow signature for request validation

        Args:
            params: Request parameters

        Returns:
            HMAC-SHA256 signature
        """
        # Sort parameters alphabetically
        sorted_params = sorted(params.items())

        # Concatenate key=value pairs
        data_string = "&".join([f"{k}={v}" for k, v in sorted_params])

        # Generate HMAC-SHA256
        signature = hmac.new(
            self.secret_key.encode(),
            data_string.encode(),
            hashlib.sha256
        ).hexdigest()

        return signature

    async def create_payment(
        self,
        amount: int,
        currency: str = "CLP",
        subject: str,
        email: str,
        payment_method: Optional[int] = None,
        url_confirmation: Optional[str] = None,
        url_return: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a payment order in Flow

        Args:
            amount: Amount in Chilean Pesos (integer, no decimals)
            currency: Currency code (default: CLP)
            subject: Payment description
            email: Customer email
            payment_method: Payment method ID (optional)
                1 = Webpay
                2 = Servipag
                3 = Multicaja
                4 = All methods
            url_confirmation: Webhook URL for confirmation
            url_return: URL to redirect user after payment
            metadata: Additional metadata (optional)

        Returns:
            Payment object with token and payment URL
        """
        logger.info(
            f"Creating Flow payment for {self.tenant}: "
            f"amount={amount} CLP, email={email}"
        )

        # Prepare parameters
        params = {
            "apiKey": self.api_key,
            "commerceOrder": f"{self.tenant}_{datetime.now().timestamp()}",
            "subject": subject,
            "currency": currency,
            "amount": amount,
            "email": email,
        }

        # Optional parameters
        if payment_method:
            params["paymentMethod"] = payment_method

        if url_confirmation:
            params["urlConfirmation"] = url_confirmation

        if url_return:
            params["urlReturn"] = url_return

        # Add metadata as optional parameters
        if metadata:
            for key, value in metadata.items():
                params[f"optional[{key}]"] = value

        # Generate signature
        params["s"] = self._generate_signature(params)

        try:
            response = await self.client.post(
                f"{self.base_url}/payment/create",
                data=params
            )
            response.raise_for_status()
            result = response.json()

            if "token" in result:
                # Add payment URL to response
                result["payment_url"] = f"{self.payment_url}?token={result['token']}"
                logger.info(f"Flow payment created: {result.get('flowOrder')}")
                return result
            else:
                logger.error(f"Flow API error: {result}")
                raise Exception(f"Flow error: {result.get('message', 'Unknown error')}")

        except httpx.HTTPError as e:
            logger.error(f"Flow API HTTP error: {str(e)}")
            raise

    async def get_payment_status(self, token: str) -> Dict[str, Any]:
        """
        Get payment status by token

        Args:
            token: Flow payment token

        Returns:
            Payment status information
        """
        logger.info(f"Getting Flow payment status: {token}")

        params = {
            "apiKey": self.api_key,
            "token": token
        }
        params["s"] = self._generate_signature(params)

        try:
            response = await self.client.get(
                f"{self.base_url}/payment/getStatus",
                params=params
            )
            response.raise_for_status()
            result = response.json()

            logger.info(f"Payment status: {result.get('status')}")
            return result

        except httpx.HTTPError as e:
            logger.error(f"Error getting payment status: {str(e)}")
            raise

    async def confirm_payment(self, token: str) -> Dict[str, Any]:
        """
        Confirm a payment (called from webhook)

        Args:
            token: Flow payment token from webhook

        Returns:
            Payment confirmation details
        """
        logger.info(f"Confirming Flow payment: {token}")

        status = await self.get_payment_status(token)

        # Check if payment is successful
        if status.get("status") == 2:  # 2 = Payment successful
            logger.info(f"Payment confirmed: {status.get('flowOrder')}")
            return {
                "status": "success",
                "flow_order": status.get("flowOrder"),
                "commerce_order": status.get("commerceOrder"),
                "amount": status.get("amount"),
                "currency": status.get("currency"),
                "payment_date": status.get("paymentDate"),
                "email": status.get("email"),
                "payment_method": self._get_payment_method_name(status.get("paymentMethod"))
            }
        elif status.get("status") == 3:  # 3 = Payment rejected
            logger.warning(f"Payment rejected: {status.get('flowOrder')}")
            return {
                "status": "failed",
                "flow_order": status.get("flowOrder"),
                "error": "Payment rejected"
            }
        else:
            logger.info(f"Payment pending: {status.get('flowOrder')}")
            return {
                "status": "pending",
                "flow_order": status.get("flowOrder")
            }

    def _get_payment_method_name(self, method_id: Optional[int]) -> str:
        """Get payment method name from ID"""
        methods = {
            1: "Webpay",
            2: "Servipag",
            3: "Multicaja",
            4: "Todos los medios",
            9: "Onepay"
        }
        return methods.get(method_id, f"Unknown ({method_id})")

    async def refund_payment(
        self,
        flow_order: int,
        amount: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Refund a payment

        Args:
            flow_order: Flow order number
            amount: Amount to refund (None = full refund)

        Returns:
            Refund confirmation
        """
        logger.info(f"Processing refund for Flow order: {flow_order}")

        params = {
            "apiKey": self.api_key,
            "refundCommerceOrder": f"{self.tenant}_refund_{datetime.now().timestamp()}",
            "flowOrder": flow_order
        }

        if amount:
            params["amount"] = amount

        params["s"] = self._generate_signature(params)

        try:
            response = await self.client.post(
                f"{self.base_url}/payment/refund",
                data=params
            )
            response.raise_for_status()
            result = response.json()

            logger.info(f"Refund created: {result.get('flowRefundOrder')}")
            return result

        except httpx.HTTPError as e:
            logger.error(f"Error creating refund: {str(e)}")
            raise

    async def get_payment_methods(self) -> Dict[str, Any]:
        """
        Get available payment methods

        Returns:
            List of available payment methods
        """
        logger.info("Getting available Flow payment methods")

        params = {
            "apiKey": self.api_key
        }
        params["s"] = self._generate_signature(params)

        try:
            response = await self.client.get(
                f"{self.base_url}/payment/getPaymentMethods",
                params=params
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error getting payment methods: {str(e)}")
            raise

    def validate_webhook_signature(
        self,
        params: Dict[str, str],
        received_signature: str
    ) -> bool:
        """
        Validate webhook signature from Flow

        Args:
            params: Webhook parameters
            received_signature: Signature received from Flow

        Returns:
            True if signature is valid
        """
        # Remove signature from params for validation
        params_copy = {k: v for k, v in params.items() if k != "s"}

        # Generate expected signature
        expected_signature = self._generate_signature(params_copy)

        # Compare signatures
        is_valid = hmac.compare_digest(expected_signature, received_signature)

        if not is_valid:
            logger.warning("Invalid Flow webhook signature")

        return is_valid

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# ============================================
# Helper Functions
# ============================================

async def get_flow_connector(tenant: str) -> FlowConnector:
    """
    Factory function to get Flow connector for specific tenant

    Args:
        tenant: Tenant identifier

    Returns:
        Configured FlowConnector instance
    """
    import os

    # Get tenant-specific Flow keys
    api_key = os.getenv(f"FLOW_API_KEY_{tenant.upper()}")
    secret_key = os.getenv(f"FLOW_SECRET_KEY_{tenant.upper()}")
    sandbox = os.getenv(f"FLOW_SANDBOX_{tenant.upper()}", "false").lower() == "true"

    if not api_key or not secret_key:
        # Fallback to default keys
        api_key = os.getenv("FLOW_API_KEY")
        secret_key = os.getenv("FLOW_SECRET_KEY")
        sandbox = os.getenv("FLOW_SANDBOX", "false").lower() == "true"

    if not api_key or not secret_key:
        raise ValueError(f"No Flow API credentials found for tenant: {tenant}")

    return FlowConnector(
        api_key=api_key,
        secret_key=secret_key,
        tenant=tenant,
        sandbox=sandbox
    )
