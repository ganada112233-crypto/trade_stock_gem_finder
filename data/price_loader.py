"""
주가 데이터 로더.

yfinance의 일괄 다운로드(yf.download)로 여러 종목의 1년치 OHLCV를
한 번에 받아온다. 종목별 개별 요청보다 훨씬 빠르고 rate limit에 안전하다.
야후 download 경로가 rate limit에 걸리면 chart JSON 엔드포인트를 단건 fallback으로 사용한다.
"""

from datetime import datetime
from typing import Dict, List, Optional
import time

import pandas as pd
import requests
import yfinance as yf
from curl_cffi import requests as curl_requests

import config
from utils.cache import cache_get, cache_set
from utils.logger import get_logger
from utils.validators import valid_price_history

log = get_logger(__name__)

_BATCH_SIZE = config.PRICE_BATCH_SIZE   # yf.download 한 번에 요청할 종목 수


def _adjust_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Adj Close가 있으면 yfinance auto_adjust=True와 비슷하게 OHLC를 보정한다."""
    if "Adj Close" not in df.columns or "Close" not in df.columns:
        return df
    close = df["Close"].replace(0, pd.NA)
    ratio = df["Adj Close"] / close
    for col in ("Open", "High", "Low", "Close"):
        if col in df.columns:
            df[col] = df[col] * ratio
    return df.drop(columns=["Adj Close"])


def _download_chart(ticker: str) -> Optional[pd.DataFrame]:
    """야후 chart JSON 엔드포인트로 단건 가격 데이터를 가져온다."""
    period2 = int(time.time())
    period1 = period2 - 370 * 24 * 3600
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {
        "period1": period1,
        "period2": period2,
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    }
    try:
        resp = requests.get(
            url,
            params=params,
            headers={"User-Agent": "Mozilla/5.0 (StockGemFinder)"},
            timeout=20,
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        log.info("가격 chart fallback 실패: %s (%s)", ticker, e)
        return None

    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        err = (payload.get("chart") or {}).get("error")
        log.info("가격 chart fallback 빈 응답: %s (%s)", ticker, err)
        return None

    item = result[0]
    timestamps = item.get("timestamp") or []
    quote = ((item.get("indicators") or {}).get("quote") or [{}])[0]
    adj = ((item.get("indicators") or {}).get("adjclose") or [{}])[0].get("adjclose")
    if not timestamps or not quote:
        return None

    df = pd.DataFrame({
        "Open": quote.get("open"),
        "High": quote.get("high"),
        "Low": quote.get("low"),
        "Close": quote.get("close"),
        "Volume": quote.get("volume"),
    }, index=pd.to_datetime(timestamps, unit="s", utc=True).tz_convert(None))
    if adj:
        df["Adj Close"] = adj
    df.index = df.index.map(lambda d: datetime(d.year, d.month, d.day))
    df = _adjust_ohlc(df).dropna(how="all")
    if valid_price_history(df, config.MIN_HISTORY_DAYS):
        return df
    log.info("가격 chart fallback 데이터 부족: %s (%d일)", ticker, len(df))
    return None


def _download_chart_batch(tickers: List[str]) -> Dict[str, pd.DataFrame]:
    """배포 환경용: chart JSON 엔드포인트로 여러 종목을 단건 순회 조회한다."""
    result: Dict[str, pd.DataFrame] = {}
    for t in tickers:
        df = _download_chart(t)
        if df is not None:
            result[t] = df
        time.sleep(0.05)
    return result


def _download_batch(tickers: List[str]) -> Dict[str, pd.DataFrame]:
    """티커 묶음 하나를 다운로드해서 {티커: OHLCV DataFrame}으로 반환."""
    result: Dict[str, pd.DataFrame] = {}
    session = curl_requests.Session()
    try:
        raw = yf.download(
            tickers=tickers,
            period=config.PRICE_HISTORY_PERIOD,
            interval="1d",
            group_by="ticker",
            auto_adjust=True,      # 배당·분할 반영된 수정 종가
            threads=False,         # 대량 스캔에서 스레드/파일 디스크립터 고갈 방지
            progress=False,
            session=session,
        )
    except Exception as e:
        log.error("가격 일괄 다운로드 실패 (%d개): %s", len(tickers), e)
        return result
    finally:
        session.close()

    if raw is None or raw.empty:
        return result

    for t in tickers:
        try:
            # 종목이 1개면 MultiIndex가 아닐 수 있다
            df = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
            df = df.dropna(how="all")
            if valid_price_history(df, config.MIN_HISTORY_DAYS):
                result[t] = df
            else:
                log.info("데이터 부족으로 제외: %s (%d일)", t, 0 if df is None else len(df))
        except (KeyError, TypeError):
            # 상장폐지·티커 변경 등으로 응답에 없는 종목
            log.info("가격 데이터 없음: %s", t)
    return result


def _download_single(ticker: str) -> Optional[pd.DataFrame]:
    """배치에서 빠진 종목을 단건으로 한 번 더 다운로드한다."""
    session = curl_requests.Session()
    try:
        df = yf.download(
            tickers=ticker,
            period=config.PRICE_HISTORY_PERIOD,
            interval="1d",
            auto_adjust=True,
            threads=False,
            progress=False,
            session=session,
        )
    except Exception as e:
        log.info("가격 단건 다운로드 실패: %s (%s)", ticker, e)
        return None
    finally:
        session.close()

    if df is None or df.empty:
        return _download_chart(ticker)
    df = df.dropna(how="all")
    if valid_price_history(df, config.MIN_HISTORY_DAYS):
        return df
    log.info("단건 가격 데이터 부족: %s (%d일)", ticker, len(df))
    return _download_chart(ticker)


def load_prices(tickers: List[str], use_cache: bool = True) -> Dict[str, pd.DataFrame]:
    """
    여러 종목의 1년치 일봉 데이터를 반환한다.
    캐시(1시간)를 먼저 확인하고, 없는 종목만 배치로 다운로드한다.
    """
    prices: Dict[str, pd.DataFrame] = {}
    missing: List[str] = []

    ttl = config.PRICE_CACHE_MINUTES * 60
    for t in tickers:
        cached = cache_get(f"price_{t}", ttl) if use_cache else None
        if cached is not None:
            prices[t] = cached
        else:
            missing.append(t)

    # 캐시에 없는 종목만 배치 다운로드
    for i in range(0, len(missing), _BATCH_SIZE):
        batch = missing[i:i + _BATCH_SIZE]
        log.info("가격 다운로드 %d~%d / %d", i + 1, i + len(batch), len(missing))
        if config.PRICE_USE_YFINANCE_BATCH:
            fetched = _download_batch(batch)
        else:
            fetched = _download_chart_batch(batch)
        if config.PRICE_USE_YFINANCE_BATCH and len(batch) > 1:
            for t in batch:
                if t not in fetched:
                    df = _download_chart(t)
                    if df is None:
                        df = _download_single(t)
                    if df is not None:
                        fetched[t] = df
        for t, df in fetched.items():
            prices[t] = df
            cache_set(f"price_{t}", df)

    return prices


def load_single_price(ticker: str) -> Optional[pd.DataFrame]:
    """상세 화면용: 종목 하나의 1년치 데이터를 반환한다."""
    result = load_prices([ticker])
    return result.get(ticker)
