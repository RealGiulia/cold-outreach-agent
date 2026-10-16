from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from .config import Settings
from .schemas import EmailDraft

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465


class MailValidationError(ValueError):
    """Raised when an outbound message fails local validation."""


def _validate_address(address: str) -> None:
    try:
        validate_email(address)
    except ValidationError as exc:
        raise MailValidationError(f"Invalid email address: {address!r}") from exc


def _compose_message(
    *,
    to_address: str,
    draft: EmailDraft,
    settings: Settings,
) -> EmailMessage:
    _validate_address(to_address)
    _validate_address(settings.gmail_address)

    if "\r" in settings.sender_name or "\n" in settings.sender_name:
        raise MailValidationError("Sender name contains invalid line breaks.")

    body = f"{draft.body.strip()}\n\n{settings.sender_signature.strip()}\n"

    message = EmailMessage()
    message["From"] = formataddr((settings.sender_name, settings.gmail_address))
    message["To"] = to_address
    message["Subject"] = draft.subject
    message.set_content(body)
    return message


def send_email(*, to_address: str, draft: EmailDraft, settings: Settings) -> None:
    message = _compose_message(to_address=to_address, draft=draft, settings=settings)
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=20) as smtp:
        smtp.login(settings.gmail_address, settings.gmail_app_password)
        smtp.send_message(message)
