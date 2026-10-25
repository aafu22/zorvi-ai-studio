"""Sending email (standard library only).

- If SMTP is configured, the message is sent in a background thread so a slow mail server never
  delays the API response (this also keeps "does this email exist?" timing identical).
- If SMTP is NOT configured and the app is not in production, the whole message, including its
  link, is printed in the backend terminal. That is how you test verification and password reset
  locally without a mail account.
- In production without SMTP nothing is printed (links are secrets); an error is logged instead.
"""

import logging
import smtplib
import threading
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger("zorvi.email")


def _deliver(to: str, subject: str, body: str) -> None:
    settings = get_settings()
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from.strip() or settings.smtp_username
    msg["To"] = to
    msg.set_content(body)
    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
                smtp.starttls()
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(msg)
    except Exception:  # never let a mail problem crash a request
        logger.exception("Could not send email to %s", to)


def send_email(to: str, subject: str, body: str) -> None:
    settings = get_settings()
    if settings.smtp_configured:
        threading.Thread(target=_deliver, args=(to, subject, body), daemon=True).start()
    elif not settings.is_production:
        logger.warning(
            "\n===== DEV EMAIL (SMTP is not configured, so nothing was sent) =====\n"
            "To: %s\nSubject: %s\n\n%s\n===================================================================",
            to,
            subject,
            body,
        )
    else:
        logger.error("SMTP is not configured; email to %s was NOT sent. Set SMTP_HOST in backend/.env.", to)


def verification_email(to: str, name: str, link: str, hours: int) -> tuple[str, str]:
    return (
        "Verify your email for Zorvi AI Studio",
        f"Hi {name},\n\nWelcome to Zorvi AI Studio. Please confirm your email address:\n\n{link}\n\n"
        f"This link works for {hours} hours. If you did not create an account, you can ignore this email.\n",
    )


def reset_email(to: str, name: str, link: str, minutes: int) -> tuple[str, str]:
    return (
        "Reset your Zorvi AI Studio password",
        f"Hi {name},\n\nWe received a request to reset your password. Choose a new one here:\n\n{link}\n\n"
        f"This link works for {minutes} minutes and can be used once. If you did not ask for this, "
        "you can ignore this email and your password will stay the same.\n",
    )
