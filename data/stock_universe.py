"""
종목 유니버스 모듈.

MVP는 S&P 500만 지원하지만, get_universe()에 이름만 추가하면
NASDAQ 100, Russell 2000 등으로 확장할 수 있는 구조다.
"""

from typing import List, Dict

import pandas as pd

import config
from utils.cache import cache_get, cache_set
from utils.logger import get_logger

log = get_logger(__name__)

# 위키피디아 접근이 막혔을 때 사용할 최소 폴백 리스트 (대표 종목 60개)
_FALLBACK_SP500 = [
    ("AAPL", "Apple Inc.", "Information Technology"),
    ("MSFT", "Microsoft", "Information Technology"),
    ("NVDA", "NVIDIA", "Information Technology"),
    ("AMZN", "Amazon", "Consumer Discretionary"),
    ("GOOGL", "Alphabet (Class A)", "Communication Services"),
    ("META", "Meta Platforms", "Communication Services"),
    ("TSLA", "Tesla", "Consumer Discretionary"),
    ("BRK-B", "Berkshire Hathaway", "Financials"),
    ("JPM", "JPMorgan Chase", "Financials"),
    ("V", "Visa", "Financials"),
    ("UNH", "UnitedHealth Group", "Health Care"),
    ("JNJ", "Johnson & Johnson", "Health Care"),
    ("XOM", "Exxon Mobil", "Energy"),
    ("CVX", "Chevron", "Energy"),
    ("PG", "Procter & Gamble", "Consumer Staples"),
    ("KO", "Coca-Cola", "Consumer Staples"),
    ("PEP", "PepsiCo", "Consumer Staples"),
    ("WMT", "Walmart", "Consumer Staples"),
    ("HD", "Home Depot", "Consumer Discretionary"),
    ("MA", "Mastercard", "Financials"),
    ("BAC", "Bank of America", "Financials"),
    ("ABBV", "AbbVie", "Health Care"),
    ("PFE", "Pfizer", "Health Care"),
    ("MRK", "Merck", "Health Care"),
    ("LLY", "Eli Lilly", "Health Care"),
    ("AVGO", "Broadcom", "Information Technology"),
    ("ORCL", "Oracle", "Information Technology"),
    ("CRM", "Salesforce", "Information Technology"),
    ("AMD", "AMD", "Information Technology"),
    ("INTC", "Intel", "Information Technology"),
    ("QCOM", "Qualcomm", "Information Technology"),
    ("CSCO", "Cisco", "Information Technology"),
    ("ADBE", "Adobe", "Information Technology"),
    ("NFLX", "Netflix", "Communication Services"),
    ("DIS", "Walt Disney", "Communication Services"),
    ("CMCSA", "Comcast", "Communication Services"),
    ("T", "AT&T", "Communication Services"),
    ("VZ", "Verizon", "Communication Services"),
    ("NKE", "Nike", "Consumer Discretionary"),
    ("MCD", "McDonald's", "Consumer Discretionary"),
    ("SBUX", "Starbucks", "Consumer Discretionary"),
    ("LOW", "Lowe's", "Consumer Discretionary"),
    ("BA", "Boeing", "Industrials"),
    ("CAT", "Caterpillar", "Industrials"),
    ("GE", "GE Aerospace", "Industrials"),
    ("UPS", "United Parcel Service", "Industrials"),
    ("HON", "Honeywell", "Industrials"),
    ("RTX", "RTX Corporation", "Industrials"),
    ("UNP", "Union Pacific", "Industrials"),
    ("GS", "Goldman Sachs", "Financials"),
    ("MS", "Morgan Stanley", "Financials"),
    ("C", "Citigroup", "Financials"),
    ("WFC", "Wells Fargo", "Financials"),
    ("TMO", "Thermo Fisher", "Health Care"),
    ("ABT", "Abbott Laboratories", "Health Care"),
    ("LIN", "Linde", "Materials"),
    ("FCX", "Freeport-McMoRan", "Materials"),
    ("NEE", "NextEra Energy", "Utilities"),
    ("DUK", "Duke Energy", "Utilities"),
    ("AMT", "American Tower", "Real Estate"),
]


def _fetch_sp500_from_wikipedia() -> pd.DataFrame:
    """위키피디아에서 S&P 500 구성 종목 표를 읽어온다."""
    # urllib 대신 requests 사용: certifi 인증서를 써서 macOS SSL 문제를 피한다
    import io
    import requests

    resp = requests.get(
        config.SP500_WIKI_URL,
        headers={"User-Agent": "Mozilla/5.0 (StockGemFinder)"},
        timeout=30,
    )
    resp.raise_for_status()
    tables = pd.read_html(io.StringIO(resp.text))
    df = tables[0]
    df = df.rename(columns={
        "Symbol": "ticker",
        "Security": "name",
        "GICS Sector": "sector",
    })[["ticker", "name", "sector"]]
    # BRK.B → BRK-B 처럼 yfinance 형식으로 변환
    df["ticker"] = df["ticker"].str.replace(".", "-", regex=False)
    return df


def get_sp500() -> pd.DataFrame:
    """
    S&P 500 종목 리스트를 반환한다 (ticker, name, sector).
    1) 파일 캐시 → 2) 위키피디아 → 3) 내장 폴백 순으로 시도한다.
    """
    cached = cache_get("sp500_universe", config.UNIVERSE_CACHE_HOURS * 3600)
    if cached is not None:
        return cached

    try:
        df = _fetch_sp500_from_wikipedia()
        if len(df) < 400:                       # 표 구조가 바뀐 경우 방어
            raise ValueError(f"S&P 500 목록이 비정상적으로 짧음: {len(df)}")
        cache_set("sp500_universe", df)
        log.info("S&P 500 %d개 종목 로드 (위키피디아)", len(df))
        return df
    except Exception as e:
        log.warning("위키피디아 로드 실패, 내장 폴백 사용: %s", e)
        return pd.DataFrame(_FALLBACK_SP500, columns=["ticker", "name", "sector"])


def get_universe(name: str = None) -> pd.DataFrame:
    """
    이름으로 종목 유니버스를 선택한다.
    향후 NASDAQ, Russell 2000 등을 여기에 추가한다.
    """
    name = name or config.UNIVERSE
    if name == "SP500":
        return get_sp500()
    # elif name == "NASDAQ100": ...   ← 확장 지점
    raise ValueError(f"지원하지 않는 유니버스: {name}")


def get_sectors(universe: pd.DataFrame) -> List[str]:
    """유니버스에 존재하는 섹터 목록을 정렬해 반환한다."""
    return sorted(universe["sector"].dropna().unique().tolist())
