from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Dict, Iterable, Any

from .config import get_settings


def send_daily_email(rankings: Iterable[Dict[str, Any]]) -> None:
    settings = get_settings()
    if not settings.gmail_user or not settings.gmail_app_password:
        raise RuntimeError("GMAIL_USER and GMAIL_APP_PASSWORD are required to send email")

    rows = list(rankings)
    msg = EmailMessage()
    msg["Subject"] = "Daily Stock Watchlist Ranking"
    msg["From"] = settings.gmail_user
    msg["To"] = settings.email_to
    msg.set_content(_render_summary(rows))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(settings.gmail_user, settings.gmail_app_password)
        smtp.send_message(msg)


def _render_summary(rows: Iterable[Dict[str, Any]]) -> str:
    lines = [
        "Daily watchlist ranking",
        "",
        "Research prioritization only, not investment advice.",
        "",
    ]
    for row in rows:
        lines.append(
            f"{row.get('final_rank')}. {row.get('ticker')} "
            f"(score {row.get('score')}): {row.get('summary')}"
        )
    return "\n".join(lines)
