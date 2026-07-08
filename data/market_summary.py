"""
시장 전반 요약.

S&P 500, NASDAQ 지수의 최근 흐름과 VIX 수준으로
"오늘 시장이 위험한지, 기회가 있는지"를 한 문장으로 요약한다.
"""

from typing import Optional
from urllib.parse import quote

import requests

import config
from utils.cache import cache_get, cache_set
from utils.logger import get_logger

log = get_logger(__name__)
_CACHE_KEY = "market_summary_v2"


def _recent_closes(ticker: str) -> list[float]:
    """야후 chart JSON 엔드포인트에서 최근 종가 배열을 가져온다."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(ticker, safe='')}"
    try:
        resp = requests.get(
            url,
            params={"range": "5d", "interval": "1d"},
            headers={"User-Agent": "Mozilla/5.0 (StockGemFinder)"},
            timeout=10,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        log.info("지수 조회 실패: %s (%s)", ticker, e)
        return []

    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        err = (payload.get("chart") or {}).get("error")
        log.info("지수 조회 빈 응답: %s (%s)", ticker, err)
        return []

    quote_data = ((result[0].get("indicators") or {}).get("quote") or [{}])[0]
    closes = quote_data.get("close") or []
    return [float(c) for c in closes if c is not None]


def _index_change_pct(ticker: str) -> Optional[float]:
    """지수의 최근 하루 등락률(%)을 반환한다."""
    closes = _recent_closes(ticker)
    if len(closes) < 2:
        return None
    return float((closes[-1] / closes[-2] - 1) * 100)


def _vix_level() -> Optional[float]:
    """VIX 최근 종가."""
    closes = _recent_closes("^VIX")
    return closes[-1] if closes else None


def get_market_summary() -> dict:
    """
    시장 요약 딕셔너리를 반환한다.
    {sp500_chg, nasdaq_chg, vix, risk_level, sentence}
    30분 캐시로 불필요한 재조회를 막는다.
    """
    cached = cache_get(_CACHE_KEY, 1800)
    if cached is not None:
        return cached

    sp500 = _index_change_pct("^GSPC")
    nasdaq = _index_change_pct("^IXIC")
    vix = _vix_level()

    # 위험도 판정: VIX 우선, 없으면 지수 등락으로 추정
    if vix is not None:
        if vix < config.VIX_CALM:
            risk_level = "안정"
        elif vix < config.VIX_NERVOUS:
            risk_level = "보통"
        else:
            risk_level = "경계"
    elif sp500 is not None and sp500 < -1.5:
        risk_level = "경계"
    else:
        risk_level = "판단 불가"

    # 자연어 요약 문장
    parts = []
    if sp500 is not None:
        direction = "상승" if sp500 >= 0 else "하락"
        parts.append(f"S&P 500이 {abs(sp500):.2f}% {direction}했습니다")
    if vix is not None:
        if risk_level == "안정":
            parts.append(f"변동성(VIX {vix:.1f})은 낮은 수준으로 시장은 비교적 차분합니다")
        elif risk_level == "보통":
            parts.append(f"변동성(VIX {vix:.1f})은 보통 수준입니다")
        else:
            parts.append(f"변동성(VIX {vix:.1f})이 높아 신중한 접근이 필요합니다")
    sentence = ". ".join(parts) + "." if parts else "시장 데이터를 불러오지 못했습니다."

    summary = {
        "sp500_chg": sp500,
        "nasdaq_chg": nasdaq,
        "vix": vix,
        "risk_level": risk_level,
        "sentence": sentence,
    }
    cache_set(_CACHE_KEY, summary)
    return summary
