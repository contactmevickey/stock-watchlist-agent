from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from stock_watchlist_agent.emailer import send_daily_email
from stock_watchlist_agent.sheets import read_watchlist, write_rankings
from stock_watchlist_agent.stock_analyzer import fetch_stock_data, rank_by_rules, rank_with_llm


def main() -> None:
    tickers = read_watchlist()
    print(f"To process {len(tickers)} stocks")
    if not tickers:
        raise RuntimeError("Watchlist tab has no tickers")

    stock_data = [fetch_stock_data(ticker) for ticker in tickers]
    print(f"Fetched data for {len(stock_data)} stocks")
    rules_rows = rank_by_rules(stock_data)
    print(f"Ranked stocks by rules: {len(rules_rows)}")
    rankings = rank_with_llm(rules_rows)
    print(f"Ranked stocks with LLM: {len(rankings)}")

    write_rankings(rankings, date.today())
    # send_daily_email(rankings)
    print(f"Processed {len(rankings)} stocks")


if __name__ == "__main__":
    main()
