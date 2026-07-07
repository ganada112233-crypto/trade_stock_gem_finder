"""
주가 데이터 로더.

yfinance의 일괄 다운로드(yf.download)로 여러 종목의 1년치 OHLCV를
한 번에 받아온다. 종목별 개별 요청보다 훨씬 빠르고 rate limit에 안전하다.
"""

from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf
from curl_cffi import requests as curl_requests

import config
from utils.cache import cache_get, cache_set
from utils.logger import get_logger
from utils.validators import valid_price_history

log = get_logger(__name__)

_BATCH_SIZE = config.PRICE_BATCH_SIZE   # yf.download 한 번에 요청할 종목 수


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
        fetched = _download_batch(batch)
        for t, df in fetched.items():
            prices[t] = df
            cache_set(f"price_{t}", df)

    return prices


def load_single_price(ticker: str) -> Optional[pd.DataFrame]:
    """상세 화면용: 종목 하나의 1년치 데이터를 반환한다."""
    result = load_prices([ticker])
    return result.get(ticker)
