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

import requests
import yfinance as yf
from curl_cffi import requests as curl_requests

import config
from utils.cache import cache_get, cache_set
from utils.logger import get_logger
from utils.validators import positive_or_none, ratio_in_range, safe_float

log = get_logger(__name__)

_MAX_WORKERS = config.FUNDAMENTAL_MAX_WORKERS    # 동시 요청 수 (너무 높이면 야후가 차단할 수 있음)
_SEC_TICKER_MAP_KEY = "sec_ticker_map"


def _safe_ratio(num: Optional[float], den: Optional[float]) -> Optional[float]:
    if num is None or den is None or den <= 0:
        return None
    return num / den


def _sec_headers() -> dict:
    return {
        "User-Agent": config.SEC_USER_AGENT,
        "Accept-Encoding": "gzip, deflate",
        "Host": "data.sec.gov",
    }


def _load_sec_ticker_map() -> Dict[str, str]:
    """SEC ticker→CIK 매핑을 반환한다."""
    cached = cache_get(_SEC_TICKER_MAP_KEY, 7 * 24 * 3600)
    if cached is not None:
        return cached

    try:
        resp = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers={"User-Agent": config.SEC_USER_AGENT},
            timeout=20,
        )
        resp.raise_for_status()
        raw = resp.json()
        mapping = {
            item["ticker"].upper().replace(".", "-"): str(item["cik_str"]).zfill(10)
            for item in raw.values()
        }
        cache_set(_SEC_TICKER_MAP_KEY, mapping)
        return mapping
    except Exception as e:
        log.info("SEC ticker map 조회 실패: %s", e)
        return {}


def _latest_unit_value(facts: dict, taxonomy: str, concepts: List[str],
                       unit: str, annual_only: bool = False) -> Optional[float]:
    """SEC facts에서 최신 값을 하나 뽑는다."""
    rows = []
    allowed_forms = {"10-K", "10-K/A"} if annual_only else {"10-K", "10-K/A", "10-Q", "10-Q/A"}
    for concept in concepts:
        items = (((facts.get(taxonomy) or {}).get(concept) or {}).get("units") or {}).get(unit) or []
        for item in items:
            if item.get("val") is None or item.get("form") not in allowed_forms:
                continue
            rows.append(item)
    if not rows:
        return None
    rows.sort(key=lambda x: (x.get("filed") or "", x.get("end") or ""))
    return safe_float(rows[-1].get("val"))


def _revenue_growth(facts: dict) -> Optional[float]:
    """최근 2개 연간 매출로 성장률을 계산한다."""
    concepts = (
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
    )
    rows = []
    for concept in concepts:
        items = (((facts.get("us-gaap") or {}).get(concept) or {}).get("units") or {}).get("USD") or []
        for item in items:
            if item.get("val") is None or item.get("form") not in {"10-K", "10-K/A"}:
                continue
            rows.append(item)
    if len(rows) < 2:
        return None
    rows.sort(key=lambda x: (x.get("fy") or 0, x.get("filed") or ""))
    latest = safe_float(rows[-1].get("val"))
    prev = safe_float(rows[-2].get("val"))
    if latest is None or prev is None or prev <= 0:
        return None
    return latest / prev - 1


def _fetch_sec_one(ticker: str, price: Optional[float]) -> Optional[dict]:
    """SEC companyfacts 기반 재무 fallback. 가격이 있어야 valuation 배수를 계산한다."""
    if price is None:
        return None
    cik = _load_sec_ticker_map().get(ticker.upper())
    if not cik:
        return None
    try:
        resp = requests.get(
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
            headers=_sec_headers(),
            timeout=20,
        )
        resp.raise_for_status()
        facts = (resp.json().get("facts") or {})
    except Exception as e:
        log.info("SEC 재무 조회 실패: %s (%s)", ticker, e)
        return None

    net_income = _latest_unit_value(
        facts, "us-gaap", ["NetIncomeLoss", "ProfitLoss"], "USD", annual_only=True
    )
    revenue = _latest_unit_value(
        facts, "us-gaap",
        ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"],
        "USD", annual_only=True,
    )
    assets = _latest_unit_value(facts, "us-gaap", ["Assets"], "USD")
    liabilities = _latest_unit_value(facts, "us-gaap", ["Liabilities"], "USD")
    equity = _latest_unit_value(
        facts, "us-gaap",
        ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
        "USD",
    )
    shares = _latest_unit_value(facts, "dei", ["EntityCommonStockSharesOutstanding"], "shares")
    market_cap = price * shares if shares else None
    book_equity = equity if equity is not None else (
        assets - liabilities if assets is not None and liabilities is not None else None
    )

    if all(v is None for v in (net_income, revenue, market_cap, book_equity)):
        return None

    return {
        "ticker": ticker,
        "per": ratio_in_range(_safe_ratio(market_cap, net_income), 0.5, 1000),
        "forward_per": None,
        "pbr": ratio_in_range(_safe_ratio(market_cap, book_equity), 0.05, 100),
        "psr": ratio_in_range(_safe_ratio(market_cap, revenue), 0.05, 100),
        "market_cap": positive_or_none(market_cap),
        "revenue_growth": _revenue_growth(facts),
        "net_income": net_income,
        "is_profitable": (net_income is not None and net_income > 0),
        "debt_to_equity": None,
        "dividend_yield": None,
        "earnings_date": "",
        "source": "SEC",
    }


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
    prices: Optional[Dict[str, float]] = None,
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

    skipped = missing[config.FUNDAMENTAL_FETCH_LIMIT:]
    missing = missing[:config.FUNDAMENTAL_FETCH_LIMIT]
    if skipped:
        log.info(
            "재무 신규 조회 제한으로 %d개를 SEC fallback으로 처리",
            len(skipped),
        )

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

    fallback_targets = [t for t in tickers if t not in results]
    for t in fallback_targets:
        data = _fetch_sec_one(t, (prices or {}).get(t))
        if data is not None:
            results[t] = data
            cache_set(f"fund_{t}", data)
        done += 1
        if progress_callback:
            progress_callback(min(done, total), total)

    log.info("재무 데이터 수집 완료: %d/%d", len(results), total)
    return results
