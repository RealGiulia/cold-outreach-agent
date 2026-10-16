from __future__ import annotations

import argparse
import smtplib
import sys
import time

from .config import ConfigurationError, Settings
from .agent import build_draft
from .mailer import MailValidationError, send_email
from .repository import count_sent_today, get_candidates, record_sent


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate personalized prospect emails with PydanticAI/OpenRouter and optionally send them via Gmail."
    )
    parser.add_argument("--limit", type=int, default=5, help="Maximum prospects in this run.")
    parser.add_argument("--prospect-id", type=int, help="Process only one prospect ID.")
    parser.add_argument(
        "--send",
        action="store_true",
        help="Actually send email. Without this flag the command is dry-run only.",
    )
    return parser.parse_args(argv)


def _print_preview(*, company: str, email: str, subject: str, body: str, signature: str) -> None:
    separator = "=" * 72
    print(f"\n{separator}\n{company} <{email}>\nSUBJECT: {subject}\n\n{body}\n\n{signature}\n{separator}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.limit <= 0:
        print("--limit must be greater than zero.", file=sys.stderr)
        return 2

    try:
        settings = Settings.from_env()
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    effective_limit = min(args.limit, settings.daily_limit)

    if args.send and (not settings.gmail_address or not settings.gmail_app_password):
        print(
            "Sending requires GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env.agent.",
            file=sys.stderr,
        )
        return 2

    if args.send:
        already_sent = count_sent_today()
        remaining = settings.daily_limit - already_sent
        if remaining <= 0:
            print(f"Daily limit reached ({settings.daily_limit}). Nothing will be sent.")
            return 0
        effective_limit = min(effective_limit, remaining)

    prospects = get_candidates(limit=effective_limit, prospect_id=args.prospect_id)
    if not prospects:
        print("No eligible prospects found.")
        return 0

    sent = 0
    failed = 0

    for index, prospect in enumerate(prospects, start=1):
        try:
            draft = build_draft(prospect, settings)
            _print_preview(
                company=prospect.company_name,
                email=prospect.contact_email,
                subject=draft.subject,
                body=draft.body,
                signature=settings.sender_signature,
            )

            if not args.send:
                continue

            send_email(
                to_address=prospect.contact_email,
                draft=draft,
                settings=settings,
            )
            record_sent(prospect.id, draft.subject)
            sent += 1
            print(f"SENT: {prospect.company_name} <{prospect.contact_email}>")

            if index < len(prospects) and settings.delay_seconds:
                time.sleep(settings.delay_seconds)
        except smtplib.SMTPAuthenticationError:
            print(
                "Gmail authentication failed. Check GMAIL_ADDRESS and the Google App Password.",
                file=sys.stderr,
            )
            return 1
        except (MailValidationError, ValueError, RuntimeError) as exc:
            failed += 1
            print(f"FAILED: {prospect.company_name}: {exc}", file=sys.stderr)
        except Exception as exc:  # keep one bad prospect from aborting the batch
            failed += 1
            print(
                f"FAILED: {prospect.company_name}: {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )

    if args.send:
        print(f"\nFinished. Sent: {sent}. Failed: {failed}.")
    else:
        print(f"\nDry-run finished. Generated {len(prospects)} draft(s). No email was sent.")

    return 1 if failed and args.send else 0
