from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
import streamlit as st

from stock_watchlist_agent.sheets import read_latest, read_ranking_for_date, read_watchlist
from stock_watchlist_agent.stock_analyzer import explain_stock, fetch_stock_data, score_stock


st.set_page_config(page_title="Stock Watchlist Agent", layout="wide")

st.title("Stock Watchlist Agent")
st.caption("Research prioritization only. Not investment advice.")

tab_latest, tab_stock, tab_history = st.tabs(["Latest Ranking", "Stock Check", "History"])

with tab_latest:
    st.subheader("Latest Ranking")
    try:
        latest = read_latest()
        if latest:
            st.dataframe(pd.DataFrame(latest), use_container_width=True, hide_index=True)
        else:
            st.info("Latest tab is empty. Run the daily job first.")
    except Exception as exc:
        st.warning(f"Could not read Latest tab: {exc}")

with tab_stock:
    st.subheader("Live Stock Check")
    try:
        watchlist = read_watchlist()
    except Exception as exc:
        watchlist = []
        st.warning(f"Could not read Watchlist tab: {exc}")

    selected = st.selectbox("Ticker", watchlist, index=0 if watchlist else None)
    custom = st.text_input("Or enter another NSE ticker")
    ticker = (custom or selected or "").strip().upper()

    if st.button("Analyze", type="primary", disabled=not ticker):
        with st.spinner(f"Fetching {ticker}..."):
            data = fetch_stock_data(ticker)
            score = score_stock(data)
            explanation = explain_stock(data, score)

        metric_cols = st.columns(4)
        metric_cols[0].metric("Score", score.score)
        metric_cols[1].metric("Price", data.current_price or "N/A")
        metric_cols[2].metric("PE", data.forward_pe or data.trailing_pe or "N/A")
        metric_cols[3].metric("PB", data.price_to_book or "N/A")
        st.write(explanation)
        st.json({"data": data.__dict__, "score": score.__dict__}, expanded=False)

with tab_history:
    st.subheader("Historical Ranking")
    selected_date = st.date_input("Ranking date", value=date.today())
    if st.button("Load History"):
        try:
            rows = read_ranking_for_date(selected_date)
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            else:
                st.info(f"No rows found for {selected_date.isoformat()}.")
        except Exception as exc:
            st.warning(f"Could not read {selected_date.isoformat()} tab: {exc}")
