from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from stock_watchlist_agent.sheets import cleanup_old_dated_tabs

# This script is intended to be run periodically, e.g. via cron, to clean up old dated tabs in the Google Sheet.
def main() -> None:
    deleted = cleanup_old_dated_tabs(days_to_keep=365)
    print(f"Deleted {len(deleted)} old tabs: {', '.join(deleted) if deleted else 'none'}")

if __name__ == "__main__":
    main()
