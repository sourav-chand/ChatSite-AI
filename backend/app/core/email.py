"""SMTP email delivery with a templating wrapper."""
from __future__ import annotations

import structlog
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema

from app.core.config import settings

log = structlog.get_logger(__name__)

_conf = ConnectionConfig(
    MAIL_USERNAME=settings.EMAIL_USER,
    MAIL_PASSWORD=settings.EMAIL_PASSWORD,
    MAIL_FROM=settings.EMAIL_FROM,
    MAIL_PORT=settings.EMAIL_PORT,
    MAIL_SERVER=settings.EMAIL_HOST,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)


async def send_email(subject: str, recipients: list[str], body: str, html: str | None = None) -> None:
    message = MessageSchema(subject=subject, recipients=recipients, body=body, html=html or body)
    try:
        await FastMail(_conf).send_message(message)
    except Exception as exc:
        log.error("email.send_failed", subject=subject, error=str(exc))


def render_template(name: str, **context: object) -> str:
    templates = {
        "verify": (
            "Welcome to ChatSite AI! Click to verify: "
            f"{settings.FRONTEND_URL}/verify-email?token={{token}}"
        ),
        "reset": (
            "Reset your password: "
            f"{settings.FRONTEND_URL}/reset-password?token={{token}}"
        ),
    }
    tmpl = templates[name]
    return tmpl.format(**context)
