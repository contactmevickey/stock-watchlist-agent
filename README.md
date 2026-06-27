# Indian Stock Watchlist Agent

Daily stock-watchlist ranking agent for NSE tickers, backed by Google Sheets, Groq, Gmail SMTP, and Streamlit.

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

### Generate a Gmail App Password

1. Go to `https://myaccount.google.com/security` and sign in to the Gmail account you want to send from.
2. Enable **2-Step Verification** if it is not already enabled.
3. Under **Signing in to Google**, select **App passwords**.
4. Create a new app password for **Mail** and copy the generated 16-character password.
5. Set `GMAIL_APP_PASSWORD` in `.env` to that generated password.

### Generate Google Service Account JSON

1. Open the Google Cloud Console: `https://console.cloud.google.com/`.
2. Create or select a project.
3. Enable the **Google Sheets API** for the project.
4. Go to **IAM & Admin > Service accounts** and create a new service account.
5. Grant the service account a role that allows Sheets access, such as **Editor** or **Sheets Editor**.
6. Create and download a JSON key for the service account.
7. Save the downloaded file as `service-account.json` in the project root, or paste the JSON into `GOOGLE_SERVICE_ACCOUNT_JSON` in `.env` as a single line.
8. Share the Google Sheet with the service account email address.

Create a `Watchlist` tab with tickers in the first column, for example:

```text
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

## Hugging Face Spaces Deployment

This app can be deployed to Hugging Face Spaces as a Streamlit app.

### Required changes

1. Keep the app entrypoint as `app.py`.
2. Make sure the Space uses `requirements.txt` for dependencies.
3. Use Hugging Face Secrets for runtime credentials instead of a local `.env` file. Set these secrets in the Space settings:
   - `GOOGLE_SHEET_ID`
   - `GOOGLE_SERVICE_ACCOUNT_JSON`
   - `GROQ_API_KEY`
   - `GMAIL_USER`
   - `GMAIL_APP_PASSWORD`
   - `EMAIL_TO`
4. If you want the app to read the service account JSON from a file inside the Space, upload `service-account.json` and optionally set `GOOGLE_SERVICE_ACCOUNT_FILE` to point to it.

### Recommended Space files

- `requirements.txt` for Python dependencies
- `app.py` as the Streamlit entrypoint
- Optional: `.streamlit/config.toml` to set the port and headless mode

### Notes

- The app expects Google Sheets access, so the Space must have valid Google credentials and the target sheet shared with the service account.
- The Streamlit UI is mainly read-only for browsing results; the daily job still needs to run from a separate process or workflow.
- If you want scheduled runs in Spaces, use a separate worker or a GitHub Action rather than relying on the Streamlit app itself.

## GitHub Actions Secrets

Add these repository secrets before enabling scheduled runs:

- `GOOGLE_SHEET_ID`
- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `GROQ_API_KEY`
- `GMAIL_USER`
- `GMAIL_APP_PASSWORD`
- `EMAIL_TO`

The daily workflow runs at `01:30 UTC`, which is `07:00 IST`.
