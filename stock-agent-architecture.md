# Indian Stock Watchlist Agent — Architecture

**Goal:** Learn agentic AI concepts hands-on by building a real tool: an agent that
analyzes a personal stock watchlist daily, ranks stocks by investment attractiveness,
emails the result, and offers a conversational UI to query stocks on demand.

**Owner:** Vickey
**Dev machine:** MacBook Air, 16GB RAM
**Status:** Architecture agreed, ready to scaffold code

---

## 1. Problem Statement

- Input: a Google Sheet ("Watchlist" tab) listing Indian (NSE) stock tickers.
- Daily (7:30 AM IST), the system should:
  1. Read the watchlist.
  2. Fetch current price + fundamentals (PE, PB, EPS, etc.) for each stock.
  3. Score each stock on valuation/fundamentals.
  4. Use an LLM to refine that ranking with qualitative judgment.
  5. Write the result to the Sheet (with history) and email a summary.
- On demand, a chat UI should let the user:
  - List watchlist stocks.
  - Ask about any individual stock's fundamentals.
  - Ask for today's (or a past day's) ranking.

**Explicit non-goal:** This is not investment advice. Output is a heuristic
prioritization tool for the user's own research, not a buy/sell signal.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  GOOGLE SHEET (multi-tab)                    │
│                                                                │
│  Tab: "Watchlist"   → input list of tickers (user-managed)    │
│  Tab: "Latest"      → always mirrors most recent ranking      │
│  Tab: "2026-06-26"  → dated historical ranking (hidden tab)   │
│  Tab: "2026-06-25"  → ...                                      │
│  (weekly cleanup job deletes dated tabs older than 365 days)  │
└───────────────────────┬───────────────────────────────────────┘
                         │
        ┌────────────────┴─────────────────┐
        │ read Watchlist                    │ write Latest + dated tab
        ▼                                    ▼
┌──────────────────────────────────────────────────────────────┐
│            GitHub Actions — daily workflow (7:30 AM IST)       │
│            run_daily.py                                        │
│                                                                  │
│  1. Read "Watchlist" tab                                         │
│  2. fetch_stock_data(ticker) for each stock (yfinance)            │
│  3. score_stock(data) → rules-based valuation score                │
│  4. rank_with_llm(all_stocks_data, scores) → Groq call;             │
│     LLM may adjust order from pure rules-ranking using                │
│     qualitative judgment, MUST return structured justification        │
│     per stock (no silent black-box reordering)                         │
│  5. Write results to "Latest" tab (overwrite) and a new dated tab       │
│  6. Send email summary to <your-email>@gmail.com                      │
└──────────────────────────────────────────────────────────────┘
                         │
                         │ reads same Sheet
                         ▼
┌──────────────────────────────────────────────────────────────┐
│            Chat UI — runs locally on Mac (Streamlit)           │
│            app.py                                                │
│                                                                    │
│  - Lists stocks from "Watchlist" tab                               │
│  - "Tell me about INFY" → live fetch + LLM explanation               │
│    (independent of daily job — analyzes fresh on demand)              │
│  - "What's today's order?" → reads "Latest" tab                       │
│  - "How did TCS rank last Monday?" → reads matching dated tab          │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│      GitHub Actions — weekly cleanup workflow                  │
│      cleanup_old_tabs.py                                        │
│      Deletes dated tabs older than 365 days                      │
└──────────────────────────────────────────────────────────────┘
```

This is two systems sharing one core analysis module:
- **Background agent** (daily job, runs unattended in the cloud)
- **Foreground agent** (chat UI, runs locally when the user wants it)

Both call into the same `stock_analyzer.py` so analysis logic isn't duplicated.

---

## 3. Components

### 3.1 Shared core module — `stock_analyzer.py`
Pure Python, no scheduling or UI logic. Used by both the daily job and the chat UI.

| Function | Responsibility |
|---|---|
| `fetch_stock_data(ticker)` | Get price, PE, PB, EPS, debt/equity, etc. via `yfinance` (`.NS` suffix for NSE). Includes basic retry + short-term caching to avoid rate-limit issues. |
| `score_stock(data)` | Deterministic rules-based valuation score (e.g. PE/PB vs sector average, debt levels, earnings trend). |
| `rank_with_llm(all_stocks_data, scores)` | Single Groq call with all stocks' data + rules-scores. Returns structured JSON: final order, and for each stock — `rules_rank`, `final_rank`, `adjustment_reason`. LLM can reorder but must justify each move. |
| `explain_stock(data, score)` | On-demand, single-stock explanation for the chat UI (plain-English summary of fundamentals + verdict). |

### 3.2 Daily job — `run_daily.py` (GitHub Actions, scheduled)
1. Auth to Google Sheets (service account).
2. Read `Watchlist` tab.
3. Call `fetch_stock_data` + `score_stock` for each ticker.
4. Call `rank_with_llm` once with the full set.
5. Write results to:
   - `Latest` tab (overwritten each run)
   - New tab named `YYYY-MM-DD` (hidden by default)
6. Send email via Gmail SMTP (app password) to `your-email@gmail.com`.

**Schedule:** GitHub Actions cron, runs in the cloud — independent of whether the
Mac is awake.

### 3.3 Weekly cleanup job — `cleanup_old_tabs.py` (GitHub Actions, scheduled)
- Runs weekly (not daily — unnecessary overhead otherwise).
- Deletes dated tabs older than 365 days.
- Leaves `Watchlist` and `Latest` untouched.

### 3.4 Chat UI — `app.py` (Streamlit, runs locally)
- Reads `Watchlist` tab to list available stocks.
- Stock-specific questions → live `fetch_stock_data` + `explain_stock` (always fresh,
  doesn't depend on the daily job having run).
- "What's the current ranking" → reads `Latest` tab.
- "What was the ranking on [date]" → reads matching dated tab if it exists.
- Runs locally since it's only needed when the user is actively interacting with it;
  no need to host it continuously.

---

## 4. Data Flow Summary

| Data | Source | Consumed by |
|---|---|---|
| Watchlist tickers | Google Sheet (`Watchlist` tab) | Daily job, Chat UI |
| Live price/fundamentals | `yfinance` | Daily job, Chat UI |
| Rules-based score | Computed in `stock_analyzer.py` | Daily job, Chat UI |
| LLM-adjusted ranking + rationale | Groq API | Daily job → written to Sheet; Chat UI reads from Sheet |
| Daily ranking history | Google Sheet (dated tabs) | Chat UI (historical queries) |
| Email summary | Generated by daily job | User's inbox |

---

## 5. Tech Stack

| Layer | Tool | Why |
|---|---|---|
| Scheduling | GitHub Actions (cron) | Free, reliable regardless of laptop state |
| Sheet access | `gspread` + Google service account | Free, standard for programmatic Sheets access |
| Stock data | `yfinance` | Free, no API key, supports NSE via `.NS` suffix |
| LLM | Groq (Llama 3.3 70B) | Free tier, fast, sufficient for this scoring/explanation task |
| Email | Gmail SMTP + app password | Free, simplest since sender/receiver are both Gmail |
| Chat UI | Streamlit | Free, fast to build a conversational interface |
| Secrets | GitHub Actions Secrets | Keeps service account keys, Groq key, Gmail app password out of source code |

---

## 6. Key Design Decisions (and why)

1. **GitHub Actions over local `launchd` for the daily job** — reliability; a local
   cron job silently fails if the Mac is asleep at 7:30 AM.
2. **Google Sheet (not a local JSON file) as shared state** — bridges the cloud job
   (GitHub Actions) and the local chat UI without extra infrastructure (e.g. a
   database or hosted API).
3. **Dated tabs for history + a `Latest` tab for convenience** — preserves full
   history for the chat UI's "how did X rank last week" use case, while keeping a
   single stable place to check today's ranking without hunting for a date.
4. **Dated tabs hidden by default** — keeps the Sheet visually clean for casual use;
   history is still fully queryable by the agent.
5. **LLM has ordering freedom, but must show its work** — the LLM can move stocks up
   or down from the pure rules-based order using qualitative judgment (sector
   context, earnings quality, etc.), but every adjustment must come with a
   structured, visible justification. This avoids a black-box ranking while still
   letting the agent reason beyond raw ratios.
6. **Weekly (not daily) cleanup** — avoids unnecessary runs; deletion only matters
   once tabs cross the 365-day mark.
7. **Hybrid scoring (rules + LLM), not pure LLM scoring** — rules-based score keeps
   the ranking grounded and explainable; LLM adds qualitative nuance on top rather
   than replacing the math entirely.

---

## 7. Known Limitations / Things to Watch

- `yfinance` is an unofficial wrapper around Yahoo Finance data — can occasionally
  break, rate-limit, or have incomplete NSE data. Build with retries and graceful
  degradation (skip + flag a stock rather than crash the whole run).
- LLM output is only as good as the data it's given — it won't catch macro events,
  breaking news, or corporate actions unless that data is explicitly fetched and
  passed in.
- This system produces a **research-prioritization tool**, not financial advice.
  Treat output accordingly.
- Google Sheets API and Groq free tiers both have rate limits — fine at watchlist
  scale (a few dozen stocks/day) but worth knowing if the watchlist grows large.

---

## 8. Build Order (suggested)

1. `stock_analyzer.py` — get `fetch_stock_data` working standalone for a few tickers.
2. Add `score_stock` (rules-based) — test against known over/undervalued stocks.
3. Add `rank_with_llm` — get structured JSON output working reliably (this is the
   trickiest prompt-engineering part).
4. `run_daily.py` — wire up Sheets read/write + email, run manually first.
5. Move `run_daily.py` into GitHub Actions, set up secrets, confirm scheduled run
   works end-to-end.
6. Add the weekly cleanup workflow.
7. Build `app.py` (Streamlit) for the chat UI, reusing `stock_analyzer.py`.
8. Polish: hide dated tabs, populate `Latest` tab, test historical queries in chat.

---

## 9. Open Items for Later (not blocking initial build)

- Exact rules-based scoring formula (sector PE/PB benchmarks, weighting) — to be
  defined when writing `score_stock`.
- Exact structured JSON schema for `rank_with_llm` output — to be defined when
  writing the prompt.
- Whether to add alerting if the daily job fails (e.g. a fallback email saying
  "today's run failed") — worth considering once the happy path works.
