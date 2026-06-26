from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    google_sheet_id: str
    google_service_account_json: Optional[str]
    groq_api_key: Optional[str]
    groq_model: str
    gmail_user: Optional[str]
    gmail_app_password: Optional[str]
    email_to: str


def get_settings() -> Settings:
    return Settings(
        google_sheet_id=os.getenv("GOOGLE_SHEET_ID", ""),
        google_service_account_json=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"),
        groq_api_key=os.getenv("GROQ_API_KEY"),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        gmail_user=os.getenv("GMAIL_USER"),
        gmail_app_password=os.getenv("GMAIL_APP_PASSWORD"),
        email_to=os.getenv("EMAIL_TO", "contactmevickey@gmail.com"),
    )


def load_service_account_info() -> Dict[str, Any]:
    raw_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw_json:
        return json.loads(raw_json)

    path = Path(os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service-account.json"))
    if path.exists():
        return json.loads(path.read_text())

    raise RuntimeError(
        "Google service account credentials missing. Set "
        "GOOGLE_SERVICE_ACCOUNT_JSON or provide service-account.json."
    )
