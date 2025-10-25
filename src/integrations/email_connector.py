"""
Gmail SMTP Email Connector for MCP Server

This connector provides email sending capabilities using Gmail SMTP.
Supports multi-tenant configuration with separate Gmail accounts per tenant.

Features:
- HTML email templates
- Attachment support
- Multi-tenant credentials
- Async email sending
- Retry logic
- Audit logging

Gmail Setup:
1. Enable 2FA on your Gmail account
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Use App Password (not your regular password)
"""

import os
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class GmailConnector:
    """Gmail SMTP connector for sending emails"""

    def __init__(self, tenant: str = "default"):
        """
        Initialize Gmail connector for a specific tenant

        Args:
            tenant: Tenant identifier (e.g., 'talleresia', 'eunacom')
        """
        self.tenant = tenant
        self.smtp_host = "smtp.gmail.com"
        self.smtp_port = 587  # TLS port

        # Load tenant-specific credentials
        tenant_suffix = f"_{tenant.upper()}" if tenant != "default" else ""

        self.smtp_user = os.getenv(f"GMAIL_SMTP_USER{tenant_suffix}")
        self.smtp_password = os.getenv(f"GMAIL_SMTP_PASSWORD{tenant_suffix}")
        self.from_email = os.getenv(
            f"GMAIL_FROM_EMAIL{tenant_suffix}",
            self.smtp_user  # Default to smtp_user if not specified
        )
        self.from_name = os.getenv(
            f"GMAIL_FROM_NAME{tenant_suffix}",
            tenant.title()
        )

        if not self.smtp_user or not self.smtp_password:
            raise ValueError(
                f"Gmail credentials not found for tenant '{tenant}'. "
                f"Set GMAIL_SMTP_USER{tenant_suffix} and GMAIL_SMTP_PASSWORD{tenant_suffix}"
            )

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        reply_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send an email via Gmail SMTP

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            text_content: Plain text fallback (optional)
            cc: List of CC email addresses
            bcc: List of BCC email addresses
            attachments: List of attachments [{"filename": "file.pdf", "content": bytes}]
            reply_to: Reply-To email address

        Returns:
            Dict with status and message_id

        Example:
            await gmail.send_email(
                to_email="alumno@example.com",
                subject="Bienvenido a TalleresIA",
                html_content="<h1>Hola!</h1><p>Gracias por inscribirte</p>"
            )
        """
        try:
            # Run SMTP in thread pool to avoid blocking
            result = await asyncio.to_thread(
                self._send_email_sync,
                to_email,
                subject,
                html_content,
                text_content,
                cc,
                bcc,
                attachments,
                reply_to,
            )

            logger.info(
                f"Email sent successfully to {to_email} "
                f"from tenant '{self.tenant}' - Subject: {subject}"
            )

            return result

        except Exception as e:
            logger.error(
                f"Failed to send email to {to_email} "
                f"from tenant '{self.tenant}': {str(e)}"
            )
            raise

    def _send_email_sync(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str],
        cc: Optional[List[str]],
        bcc: Optional[List[str]],
        attachments: Optional[List[Dict[str, Any]]],
        reply_to: Optional[str],
    ) -> Dict[str, Any]:
        """Synchronous email sending (called in thread pool)"""

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = to_email

        if cc:
            msg["Cc"] = ", ".join(cc)
        if reply_to:
            msg["Reply-To"] = reply_to

        # Add plain text version (fallback)
        if text_content:
            part1 = MIMEText(text_content, "plain", "utf-8")
            msg.attach(part1)

        # Add HTML version
        part2 = MIMEText(html_content, "html", "utf-8")
        msg.attach(part2)

        # Add attachments
        if attachments:
            for attachment in attachments:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment["content"])
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {attachment['filename']}",
                )
                msg.attach(part)

        # Send email
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()  # Upgrade to secure connection
            server.login(self.smtp_user, self.smtp_password)

            # Prepare recipients list
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            server.sendmail(self.from_email, recipients, msg.as_string())

        # Generate message ID for tracking
        message_id = f"{int(datetime.now().timestamp())}_{self.tenant}_{to_email}"

        return {
            "status": "sent",
            "message_id": message_id,
            "to": to_email,
            "subject": subject,
            "sent_at": datetime.now().isoformat(),
            "tenant": self.tenant,
        }

    async def send_template_email(
        self,
        to_email: str,
        template_name: str,
        context: Dict[str, Any],
        subject: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Send email using a template

        Args:
            to_email: Recipient email
            template_name: Name of template (e.g., 'payment_confirmation')
            context: Template variables (e.g., {'customer_name': 'Juan', 'amount': 50000})
            subject: Email subject (uses template default if not provided)
            **kwargs: Additional arguments passed to send_email()

        Example:
            await gmail.send_template_email(
                to_email="alumno@example.com",
                template_name="payment_confirmation",
                context={
                    "customer_name": "Juan Pérez",
                    "amount": 50000,
                    "course_name": "Taller IA Básico",
                    "payment_date": "2024-01-15"
                }
            )
        """
        template = self._load_template(template_name)

        # Render template with context
        html_content = template["html"]
        text_content = template.get("text")
        template_subject = template.get("subject", "Notificación")

        # Replace placeholders in template
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"  # {{key}}
            html_content = html_content.replace(placeholder, str(value))
            if text_content:
                text_content = text_content.replace(placeholder, str(value))
            if subject is None:
                template_subject = template_subject.replace(placeholder, str(value))

        final_subject = subject or template_subject

        return await self.send_email(
            to_email=to_email,
            subject=final_subject,
            html_content=html_content,
            text_content=text_content,
            **kwargs,
        )

    def _load_template(self, template_name: str) -> Dict[str, str]:
        """Load email template from file"""
        templates_dir = Path(__file__).parent.parent / "templates" / "emails"

        template_file = templates_dir / f"{template_name}.html"

        if not template_file.exists():
            # Return default template if not found
            logger.warning(f"Template '{template_name}' not found, using default")
            return {
                "subject": "Notificación",
                "html": "<p>{{message}}</p>",
                "text": "{{message}}",
            }

        with open(template_file, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Try to load corresponding text version
        text_file = templates_dir / f"{template_name}.txt"
        text_content = None
        if text_file.exists():
            with open(text_file, "r", encoding="utf-8") as f:
                text_content = f.read()

        # Try to load subject from metadata
        meta_file = templates_dir / f"{template_name}.meta"
        subject = "Notificación"
        if meta_file.exists():
            with open(meta_file, "r", encoding="utf-8") as f:
                subject = f.read().strip()

        return {
            "html": html_content,
            "text": text_content,
            "subject": subject,
        }


# Common email templates for quick use
class EmailTemplates:
    """Pre-built email templates"""

    @staticmethod
    def payment_confirmation(
        customer_name: str,
        amount: int,
        currency: str,
        description: str,
        payment_date: str,
    ) -> Dict[str, str]:
        """Generate payment confirmation email"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 20px; }}
                .amount {{ font-size: 32px; font-weight: bold; color: #4CAF50; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ ¡Pago Confirmado!</h1>
                </div>
                <div class="content">
                    <p>Hola {customer_name},</p>
                    <p>Tu pago ha sido procesado exitosamente.</p>

                    <h2>Detalles del pago:</h2>
                    <p><strong>Descripción:</strong> {description}</p>
                    <p><strong>Monto:</strong> <span class="amount">{amount:,} {currency}</span></p>
                    <p><strong>Fecha:</strong> {payment_date}</p>

                    <p>Gracias por tu compra. Recibirás más información pronto.</p>
                </div>
                <div class="footer">
                    <p>Este es un email automático, por favor no respondas.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text = f"""
        ✅ ¡Pago Confirmado!

        Hola {customer_name},

        Tu pago ha sido procesado exitosamente.

        Detalles del pago:
        - Descripción: {description}
        - Monto: {amount:,} {currency}
        - Fecha: {payment_date}

        Gracias por tu compra.
        """

        return {
            "subject": "Confirmación de pago - Tu transacción fue exitosa",
            "html": html,
            "text": text,
        }

    @staticmethod
    def subscription_activated(
        customer_name: str,
        plan_name: str,
        amount: int,
        currency: str,
        next_billing_date: str,
    ) -> Dict[str, str]:
        """Generate subscription activation email"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2196F3; color: white; padding: 20px; text-align: center; }}
                .content {{ background: #f9f9f9; padding: 20px; }}
                .plan {{ font-size: 24px; font-weight: bold; color: #2196F3; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 ¡Suscripción Activada!</h1>
                </div>
                <div class="content">
                    <p>Hola {customer_name},</p>
                    <p>Tu suscripción ha sido activada correctamente.</p>

                    <h2>Detalles de la suscripción:</h2>
                    <p><strong>Plan:</strong> <span class="plan">{plan_name}</span></p>
                    <p><strong>Monto mensual:</strong> {amount:,} {currency}</p>
                    <p><strong>Próximo cobro:</strong> {next_billing_date}</p>

                    <p>Tu tarjeta será cobrada automáticamente cada mes.</p>
                    <p>Puedes cancelar en cualquier momento desde tu cuenta.</p>
                </div>
                <div class="footer">
                    <p>Gracias por suscribirte.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text = f"""
        🎉 ¡Suscripción Activada!

        Hola {customer_name},

        Tu suscripción ha sido activada correctamente.

        Detalles:
        - Plan: {plan_name}
        - Monto mensual: {amount:,} {currency}
        - Próximo cobro: {next_billing_date}

        Tu tarjeta será cobrada automáticamente cada mes.
        """

        return {
            "subject": f"Suscripción activada - {plan_name}",
            "html": html,
            "text": text,
        }
