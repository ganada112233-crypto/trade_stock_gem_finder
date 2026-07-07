"""
데이터 검증 헬퍼.

yfinance가 돌려주는 값에는 None, NaN, 0, 음수, 문자열 등이 섞여 있다.
점수 계산 전에 반드시 이 모듈로 정리해서 안전한 값만 사용한다.
"""

import math
from typing import Any, Optional

import pandas as pd


def safe_float(value: Any) -> Optional[float]:
    """float로 변환 가능하고 유한한 값이면 반환, 아니면 None."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def positive_or_none(value: Any) -> Optional[float]:
    """양수만 허용. PER/PBR/PSR처럼 음수가 의미 없는 지표에 사용."""
    f = safe_float(value)
    if f is None or f <= 0:
        return None
    return f


def ratio_in_range(value: Any, lo: float, hi: float) -> Optional[float]:
    """
    PER/PBR/PSR용: 상식적인 범위를 벗어난 값은 None 처리한다.
    (yfinance는 가끔 0.0004나 40000 같은 비정상 값을 돌려준다)
    """
    f = positive_or_none(value)
    if f is None or f < lo or f > hi:
        return None
    return f


def valid_price_history(df: Optional[pd.DataFrame], min_days: int) -> bool:
    """지표 계산이 가능한 주가 데이터인지 확인한다."""
    if df is None or df.empty:
        return False
    if len(df) < min_days:
        return False
    required = {"Open", "High", "Low", "Close", "Volume"}
    if not required.issubset(df.columns):
        return False
    # 종가가 전부 NaN이면 사용 불가
    return df["Close"].notna().sum() >= min_days
