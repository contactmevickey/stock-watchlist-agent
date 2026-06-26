from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List

import gspread
from google.oauth2.service_account import Credentials

from .config import get_settings, load_service_account_info


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
WATCHLIST_TABS = ("Watchlist", "My watchlist")
SYSTEM_TABS = {"Latest", *WATCHLIST_TABS}


def get_spreadsheet() -> gspread.Spreadsheet:
    settings = get_settings()
    if not settings.google_sheet_id:
        raise RuntimeError("GOOGLE_SHEET_ID is required")
    credentials = Credentials.from_service_account_info(
        load_service_account_info(),
        scopes=SCOPES,
    )
    client = gspread.authorize(credentials)
    return client.open_by_key(settings.google_sheet_id)


def read_watchlist() -> List[str]:
    spreadsheet = get_spreadsheet()
    sheet = _first_existing_worksheet(spreadsheet, WATCHLIST_TABS)
    values = sheet.col_values(1)
    tickers = []
    for value in values:
        ticker = value.strip().upper()
        if ticker and ticker != "TICKER":
            tickers.append(ticker)
    return tickers


def read_latest() -> List[Dict[str, Any]]:
    try:
        return get_spreadsheet().worksheet("Latest").get_all_records()
    except gspread.WorksheetNotFound:
        return []


def read_ranking_for_date(day: date) -> List[Dict[str, Any]]:
    try:
        return get_spreadsheet().worksheet(day.isoformat()).get_all_records()
    except gspread.WorksheetNotFound:
        return []


def write_rankings(rankings: Iterable[Dict[str, Any]], run_date: date) -> None:
    spreadsheet = get_spreadsheet()
    rows = list(rankings)
    values = _ranking_values(rows, run_date)
    _upsert_values(spreadsheet, "Latest", values)
    dated_sheet = _upsert_values(spreadsheet, run_date.isoformat(), values)
    dated_sheet.hide()


def cleanup_old_dated_tabs(days_to_keep: int = 365) -> List[str]:
    spreadsheet = get_spreadsheet()
    cutoff = date.today() - timedelta(days=days_to_keep)
    deleted = []
    for worksheet in spreadsheet.worksheets():
        title = worksheet.title
        if title in SYSTEM_TABS:
            continue
        try:
            tab_date = datetime.strptime(title, "%Y-%m-%d").date()
        except ValueError:
            continue
        if tab_date < cutoff:
            spreadsheet.del_worksheet(worksheet)
            deleted.append(title)
    return deleted


def _upsert_values(
    spreadsheet: gspread.Spreadsheet,
    title: str,
    values: List[List[Any]],
) -> gspread.Worksheet:
    try:
        worksheet = spreadsheet.worksheet(title)
        worksheet.clear()
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=title, rows=max(len(values), 20), cols=10)
    worksheet.update(values=values, range_name="A1")
    return worksheet


def _first_existing_worksheet(
    spreadsheet: gspread.Spreadsheet,
    titles: Iterable[str],
) -> gspread.Worksheet:
    for title in titles:
        try:
            return spreadsheet.worksheet(title)
        except gspread.WorksheetNotFound:
            continue
    expected = " or ".join(f"'{title}'" for title in titles)
    raise gspread.WorksheetNotFound(f"Could not find {expected} tab")


def _ranking_values(rows: List[Dict[str, Any]], run_date: date) -> List[List[Any]]:
    header = [
        "Run Date",
        "Final Rank",
        "Ticker",
        "Rules Rank",
        "Score",
        "Summary",
        "Adjustment Reason",
    ]
    body = [
        [
            run_date.isoformat(),
            row.get("final_rank"),
            row.get("ticker"),
            row.get("rules_rank"),
            row.get("score"),
            row.get("summary"),
            row.get("adjustment_reason"),
        ]
        for row in rows
    ]
    return [header] + body
