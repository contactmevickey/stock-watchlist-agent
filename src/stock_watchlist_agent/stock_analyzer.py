from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

import yfinance as yf
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import get_settings


@dataclass
class StockData:
    ticker: str
    yahoo_ticker: str
    name: str
    sector: str
    current_price: Optional[float]
    market_cap: Optional[float]
    trailing_pe: Optional[float]
    forward_pe: Optional[float]
    price_to_book: Optional[float]
    eps: Optional[float]
    debt_to_equity: Optional[float]
    return_on_equity: Optional[float]
    revenue_growth: Optional[float]
    profit_margins: Optional[float]
    dividend_yield: Optional[float]
    fifty_two_week_low: Optional[float]
    fifty_two_week_high: Optional[float]
    fetched_at: str
    error: Optional[str] = None


@dataclass
class StockScore:
    ticker: str
    score: float
    valuation_score: float
    quality_score: float
    growth_score: float
    risk_score: float
    notes: List[str]


def normalize_nse_ticker(ticker: str) -> str:
    cleaned = ticker.strip().upper()
    if not cleaned:
        raise ValueError("Ticker cannot be empty")
    if "." in cleaned:
        return cleaned
    return f"{cleaned}.NS"


def _num(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(3))
def fetch_stock_data(ticker: str) -> StockData:
    yahoo_ticker = normalize_nse_ticker(ticker)
    base_ticker = yahoo_ticker.replace(".NS", "")
    fetched_at = datetime.now(timezone.utc).isoformat()

    try:
        stock = yf.Ticker(yahoo_ticker)
        info = stock.info or {}
        fast_info = getattr(stock, "fast_info", {}) or {}

        current_price = _num(
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or fast_info.get("last_price")
        )

        return StockData(
            ticker=base_ticker,
            yahoo_ticker=yahoo_ticker,
            name=info.get("longName") or info.get("shortName") or base_ticker,
            sector=info.get("sector") or "Unknown",
            current_price=current_price,
            market_cap=_num(info.get("marketCap")),
            trailing_pe=_num(info.get("trailingPE")),
            forward_pe=_num(info.get("forwardPE")),
            price_to_book=_num(info.get("priceToBook")),
            eps=_num(info.get("trailingEps")),
            debt_to_equity=_num(info.get("debtToEquity")),
            return_on_equity=_num(info.get("returnOnEquity")),
            revenue_growth=_num(info.get("revenueGrowth")),
            profit_margins=_num(info.get("profitMargins")),
            dividend_yield=_num(info.get("dividendYield")),
            fifty_two_week_low=_num(info.get("fiftyTwoWeekLow")),
            fifty_two_week_high=_num(info.get("fiftyTwoWeekHigh")),
            fetched_at=fetched_at,
        )
    except Exception as exc:
        print(f"Failure for stock {yahoo_ticker}: {exc}")
        return StockData(
            ticker=base_ticker,
            yahoo_ticker=yahoo_ticker,
            name=base_ticker,
            sector="Unknown",
            current_price=None,
            market_cap=None,
            trailing_pe=None,
            forward_pe=None,
            price_to_book=None,
            eps=None,
            debt_to_equity=None,
            return_on_equity=None,
            revenue_growth=None,
            profit_margins=None,
            dividend_yield=None,
            fifty_two_week_low=None,
            fifty_two_week_high=None,
            fetched_at=fetched_at,
            error=str(exc),
        )


def score_stock(data: StockData) -> StockScore:
    notes: List[str] = []

    valuation = 50.0
    pe = data.forward_pe or data.trailing_pe
    if pe is None:
        notes.append("PE unavailable")
    elif pe <= 15:
        valuation += 25
        notes.append("Attractive PE")
    elif pe <= 30:
        valuation += 10
        notes.append("Moderate PE")
    elif pe > 60:
        valuation -= 25
        notes.append("Very high PE")
    else:
        valuation -= 10
        notes.append("Elevated PE")

    if data.price_to_book is None:
        notes.append("PB unavailable")
    elif data.price_to_book <= 2:
        valuation += 15
        notes.append("Attractive PB")
    elif data.price_to_book > 8:
        valuation -= 15
        notes.append("High PB")

    quality = 50.0
    if data.return_on_equity is not None:
        roe_pct = data.return_on_equity * 100
        if roe_pct >= 20:
            quality += 25
            notes.append("Strong ROE")
        elif roe_pct >= 12:
            quality += 10
            notes.append("Healthy ROE")
        elif roe_pct < 5:
            quality -= 20
            notes.append("Weak ROE")
    else:
        notes.append("ROE unavailable")

    if data.profit_margins is not None:
        margin_pct = data.profit_margins * 100
        if margin_pct >= 15:
            quality += 15
            notes.append("Strong margins")
        elif margin_pct < 5:
            quality -= 15
            notes.append("Thin margins")

    growth = 50.0
    if data.revenue_growth is not None:
        growth_pct = data.revenue_growth * 100
        if growth_pct >= 15:
            growth += 25
            notes.append("Strong revenue growth")
        elif growth_pct >= 5:
            growth += 10
            notes.append("Positive revenue growth")
        elif growth_pct < 0:
            growth -= 20
            notes.append("Revenue declining")
    else:
        notes.append("Revenue growth unavailable")

    risk = 50.0
    if data.debt_to_equity is not None:
        if data.debt_to_equity <= 50:
            risk += 20
            notes.append("Manageable debt")
        elif data.debt_to_equity >= 150:
            risk -= 25
            notes.append("High debt")
    else:
        notes.append("Debt/equity unavailable")

    if data.current_price and data.fifty_two_week_high and data.fifty_two_week_low:
        range_size = data.fifty_two_week_high - data.fifty_two_week_low
        if range_size > 0:
            range_position = (data.current_price - data.fifty_two_week_low) / range_size
            if range_position <= 0.35:
                valuation += 8
                notes.append("Trading closer to 52-week low")
            elif range_position >= 0.85:
                valuation -= 8
                notes.append("Trading near 52-week high")

    if data.error:
        notes.append(f"Data fetch issue: {data.error}")
        valuation -= 20
        quality -= 20
        growth -= 20
        risk -= 20

    valuation = _clamp(valuation)
    quality = _clamp(quality)
    growth = _clamp(growth)
    risk = _clamp(risk)
    total = round(valuation * 0.35 + quality * 0.30 + growth * 0.20 + risk * 0.15, 2)

    return StockScore(
        ticker=data.ticker,
        score=total,
        valuation_score=valuation,
        quality_score=quality,
        growth_score=growth,
        risk_score=risk,
        notes=notes,
    )


def _clamp(value: float, lower: float = 0, upper: float = 100) -> float:
    return round(max(lower, min(upper, value)), 2)


def rank_by_rules(stock_data: Iterable[StockData]) -> List[Dict[str, Any]]:
    rows = []
    for data in stock_data:
        score = score_stock(data)
        rows.append({"data": data, "score": score})
    rows.sort(key=lambda item: item["score"].score, reverse=True)
    for index, row in enumerate(rows, start=1):
        row["rules_rank"] = index
    return rows


def rank_with_llm(stock_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    settings = get_settings()
    if not settings.groq_api_key:
        return _fallback_llm_ranking(stock_rows, "GROQ_API_KEY not configured")

    payload = [
        {
            "rules_rank": row["rules_rank"],
            "stock": asdict(row["data"]),
            "score": asdict(row["score"]),
        }
        for row in stock_rows
    ]
    print(f"Sending {len(payload)} stocks to LLM for ranking")

    prompt = (
        "Act and Analyse as an Expert Stock Market Analyst. I need you to rank Indian NSE watchlist stocks for research prioritization."
        "Initial data based analysis and scoring is done as an stock market investor myself, and you must use the rules score as the anchor, "
        "adjusting only when the supplied fundamentals justify it, and return strict JSON with a 'rankings' array. "
        "Each item must include ticker, rules_rank, final_rank, score, adjustment_reason, and summary."
        "You should rank all stocks, even if the score is low, and provide a concise summary of the stock's fundamentals."
        "You as an expert in stock market analysis, can consider other criteria that can be considered as well along with the supplied fundamentals, "
        "go ahead and update rank as required, but you must justify it in the adjustment_reason for the rank order changes for that stock."
        "If you cannot rank a stock, provide a reason in adjustment_reason and use the rules_rank as final_rank."
    )

    client = Groq(api_key=settings.groq_api_key)
    try:
        response = client.chat.completions.create(
            model=settings.groq_model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(payload, default=str)},
            ],
        )
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        rankings = parsed.get("rankings", [])
        print(f"LLM returned {len(rankings)} rankings")

        if not isinstance(rankings, list) or not rankings:
            raise ValueError("LLM returned no rankings")
        return sorted(rankings, key=lambda item: item.get("final_rank", 999))
    except Exception as exc:
        print(f"Error occurred while fetching LLM rankings: {exc}")
        return _fallback_llm_ranking(stock_rows, f"LLM ranking failed: {exc}")


def _fallback_llm_ranking(stock_rows: List[Dict[str, Any]], reason: str) -> List[Dict[str, Any]]:
    return [
        {
            "ticker": row["data"].ticker,
            "rules_rank": row["rules_rank"],
            "final_rank": row["rules_rank"],
            "score": row["score"].score,
            "adjustment_reason": reason,
            "summary": "; ".join(row["score"].notes[:4]) or "Rules-based rank used.",
        }
        for row in stock_rows
    ]


def explain_stock(data: StockData, score: Optional[StockScore] = None) -> str:
    score = score or score_stock(data)
    settings = get_settings()
    facts = {"stock": asdict(data), "score": asdict(score)}

    if not settings.groq_api_key:
        return _fallback_explanation(data, score)

    client = Groq(api_key=settings.groq_api_key)
    try:
        response = client.chat.completions.create(
            model=settings.groq_model,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Explain this stock's supplied fundamentals in plain English. "
                        "Do not give buy/sell advice. Keep it concise."
                    ),
                },
                {"role": "user", "content": json.dumps(facts, default=str)},
            ],
        )
        return response.choices[0].message.content or _fallback_explanation(data, score)
    except Exception:
        return _fallback_explanation(data, score)


def _fallback_explanation(data: StockData, score: StockScore) -> str:
    return (
        f"{data.ticker} scores {score.score}/100 on the starter rules model. "
        f"Key notes: {'; '.join(score.notes[:6]) or 'not enough data available'}. "
        "Use this as research prioritization, not investment advice."
    )
