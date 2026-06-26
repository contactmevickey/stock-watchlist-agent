# Indian Stock Watchlist Agent

Daily stock-watchlist ranking agent for NSE/BSE tickers, backed by Google Sheets, yfinance, Groq, Gmail SMTP, and Streamlit.

## Local Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env` with:

- `GOOGLE_SHEET_ID`: the spreadsheet ID from the Google Sheet URL.
- `GOOGLE_SERVICE_ACCOUNT_JSON`: full service-account JSON as one line, or use a local `service-account.json`.
- `GROQ_API_KEY`: Groq API key.
- `GMAIL_USER`: Gmail sender address.
- `GMAIL_APP_PASSWORD`: Gmail app password.
- `EMAIL_TO`: destination email.

Share the Google Sheet with the service account email. Create a `Watchlist` tab with tickers in the first column, for example:

```text
Ticker
INFY
TCS
RELIANCE
```

## Run Locally

```bash
source venv/bin/activate
python scripts/run_daily.py
streamlit run app.py
```

## GitHub Actions Secrets

Add these repository secrets before enabling scheduled runs:

- `GOOGLE_SHEET_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `GROQ_API_KEY`
- `GMAIL_USER`
- `GMAIL_APP_PASSWORD`
- `EMAIL_TO`

The daily workflow runs at `02:00 UTC`, which is `07:30 IST`.
