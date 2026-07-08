"""
기본 재무 데이터 로더.

yfinance의 Ticker.info에서 PER, PBR, PSR, 시가총액, 매출 성장률,
순이익 여부, 부채비율, 배당수익률을 뽑아온다.

.info 호출은 종목당 1번의 HTTP 요청이라 느리다.
→ ThreadPoolExecutor로 병렬화하고, 24시간 파일 캐시를 사용한다.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from typing import Callable, Dict, List, Optional

import yfinance as yf
from curl_cffi import requests as curl_requests

import config
from utils.cache import cache_get, cache_set
from utils.logger import get_logger
from utils.validators import positive_or_none, ratio_in_range, safe_float

log = get_logger(__name__)

_MAX_WORKERS = config.FUNDAMENTAL_MAX_WORKERS    # 동시 요청 수 (너무 높이면 야후가 차단할 수 있음)


def _fetch_one(ticker: str) -> Optional[dict]:
    """종목 하나의 재무 스냅샷을 만든다. 실패 시 None."""
    info = {}
    last_error = None
    for attempt in range(config.FUNDAMENTAL_RETRY_COUNT + 1):
        session = curl_requests.Session()
        try:
            info = yf.Ticker(ticker, session=session).info or {}
            break
        except Exception as e:
            last_error = e
            if attempt < config.FUNDAMENTAL_RETRY_COUNT:
                wait = config.FUNDAMENTAL_RETRY_SLEEP * (attempt + 1)
                log.info("재무 데이터 재시도 대기: %s (%s, %.1f초)", ticker, e, wait)
                time.sleep(wait)
            else:
                log.info("재무 데이터 조회 실패: %s (%s)", ticker, e)
                return None
        finally:
            session.close()

    time.sleep(config.FUNDAMENTAL_REQUEST_SLEEP)

    if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
        # 응답은 왔지만 내용이 비어있는 경우 (상장폐지 등)
        if len(info) < 5:
            if last_error:
                log.info("재무 데이터 빈 응답: %s (%s)", ticker, last_error)
            return None

    net_income = safe_float(info.get("netIncomeToCommon"))
    return {
        "ticker": ticker,
        "per": ratio_in_range(info.get("trailingPE"), 0.5, 1000),
        "forward_per": ratio_in_range(info.get("forwardPE"), 0.5, 1000),
        "pbr": ratio_in_range(info.get("priceToBook"), 0.05, 100),
        "psr": ratio_in_range(info.get("priceToSalesTrailing12Months"), 0.05, 100),
        "market_cap": positive_or_none(info.get("marketCap")),
        "revenue_growth": safe_float(info.get("revenueGrowth")),        # 소수 (0.12 = 12%)
        "net_income": net_income,
        "is_profitable": (net_income is not None and net_income > 0),
        "debt_to_equity": safe_float(info.get("debtToEquity")),         # % 단위
        "dividend_yield": safe_float(info.get("dividendYield")),
        "earnings_date": str(info.get("earningsTimestamp") or ""),      # 실적일 (있으면)
    }


def load_fundamentals(
    tickers: List[str],
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Dict[str, dict]:
    """
    여러 종목의 재무 스냅샷을 병렬로 수집한다.
    progress_callback(완료 수, 전체 수)로 UI 진행률을 갱신할 수 있다.
    """
    results: Dict[str, dict] = {}
    missing: List[str] = []

    ttl = config.FUNDAMENTAL_CACHE_HOURS * 3600
    for t in tickers:
        cached = cache_get(f"fund_{t}", ttl)
        if cached is not None:
            results[t] = cached
        else:
            missing.append(t)

    done = len(results)
    total = len(tickers)
    if progress_callback:
        progress_callback(done, total)

    if not missing:
        return results

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
        futures = {pool.submit(_fetch_one, t): t for t in missing}
        for future in as_completed(futures):
            t = futures[future]
            try:
                data = future.result()
            except Exception as e:          # 개별 실패가 전체를 막지 않도록
                log.warning("재무 수집 예외: %s (%s)", t, e)
                data = None
            if data is not None:
                results[t] = data
                cache_set(f"fund_{t}", data)
            done += 1
            if progress_callback:
                progress_callback(done, total)

    log.info("재무 데이터 수집 완료: %d/%d", len(results), total)
    return results
