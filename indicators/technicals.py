"""
기술적 지표 계산.

pandas만으로 RSI, 이동평균, 거래량 비율, 수익률, 변동성을 계산한다.
(pandas-ta는 최신 numpy와 호환 문제가 있어 직접 구현)

compute_technicals(df) 하나만 호출하면 점수 계산에 필요한
모든 지표가 담긴 딕셔너리를 돌려준다.
"""

from typing import Optional

import numpy as np
import pandas as pd

import config
from utils.validators import valid_price_history


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder 방식 RSI. TradingView/HTS와 동일한 계산."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    # Wilder smoothing = EMA(alpha=1/period)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(100.0).where(avg_loss.notna(), np.nan)  # 손실 0이면 RSI 100


def compute_technicals(df: pd.DataFrame) -> Optional[dict]:
    """
    1년치 OHLCV DataFrame에서 지표 스냅샷을 계산한다.
    데이터가 부족하면 None을 반환한다 (→ '데이터 부족' 처리).
    """
    if not valid_price_history(df, config.MIN_HISTORY_DAYS):
        return None

    close = df["Close"]
    volume = df["Volume"].fillna(0)

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    rsi_series = rsi(close)

    last = -1       # 가장 최근 거래일
    prev = -2

    price = float(close.iloc[last])
    prev_price = float(close.iloc[prev])

    # 거래량: 당일 vs 20일 평균 (당일 제외한 직전 20일 평균과 비교)
    vol_today = float(volume.iloc[last])
    vol_avg20 = float(volume.iloc[-21:-1].mean()) if len(volume) >= 21 else float(volume.mean())
    volume_ratio = vol_today / vol_avg20 if vol_avg20 > 0 else 0.0

    # 수익률
    ret_1d = price / prev_price - 1
    ret_5d = price / float(close.iloc[-6]) - 1 if len(close) >= 6 else None
    ret_20d = price / float(close.iloc[-21]) - 1 if len(close) >= 21 else None

    # 20일 이동평균 상향 돌파: 어제는 아래, 오늘은 위
    cross_sma20 = bool(
        not np.isnan(sma20.iloc[last]) and not np.isnan(sma20.iloc[prev])
        and prev_price <= sma20.iloc[prev] and price > sma20.iloc[last]
    )

    # 골든크로스(20/50): 최근 3일 이내 발생했는지
    golden_cross = False
    if not sma50.iloc[last:].isna().any() and len(sma20) >= 53:
        diff = (sma20 - sma50).iloc[-4:]
        if diff.notna().all():
            golden_cross = bool(diff.iloc[0] <= 0 and diff.iloc[-1] > 0)

    # RSI 반등 여부: RSI가 저점 대비 상승 중인지
    rsi_now = float(rsi_series.iloc[last]) if not np.isnan(rsi_series.iloc[last]) else None
    rsi_prev = float(rsi_series.iloc[prev]) if not np.isnan(rsi_series.iloc[prev]) else None
    rsi_rising = bool(rsi_now is not None and rsi_prev is not None and rsi_now > rsi_prev)
    rsi_min_5d = float(rsi_series.iloc[-5:].min()) if rsi_series.iloc[-5:].notna().all() else None

    # 당일 양봉 여부
    green_candle = bool(price > float(df["Open"].iloc[last]))

    # 연환산 변동성 (최근 20일 일간수익률 표준편차 × √252)
    daily_ret = close.pct_change().iloc[-20:]
    volatility = float(daily_ret.std() * np.sqrt(252)) if daily_ret.notna().sum() >= 10 else None

    # 평균 거래대금 ($) - 유동성 판단용
    avg_dollar_volume = float((close * volume).iloc[-20:].mean())

    return {
        "price": price,
        "change_pct": ret_1d * 100,
        "volume_today": vol_today,
        "volume_avg20": vol_avg20,
        "volume_ratio": volume_ratio,
        "avg_dollar_volume": avg_dollar_volume,
        "sma20": float(sma20.iloc[last]) if not np.isnan(sma20.iloc[last]) else None,
        "sma50": float(sma50.iloc[last]) if not np.isnan(sma50.iloc[last]) else None,
        "sma200": float(sma200.iloc[last]) if not np.isnan(sma200.iloc[last]) else None,
        "rsi": rsi_now,
        "rsi_rising": rsi_rising,
        "rsi_min_5d": rsi_min_5d,
        "ret_5d": ret_5d,
        "ret_20d": ret_20d,
        "cross_sma20": cross_sma20,
        "golden_cross": golden_cross,
        "green_candle": green_candle,
        "volatility": volatility,
    }


def add_chart_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """상세 차트용: SMA/RSI 컬럼을 붙인 복사본을 반환한다."""
    out = df.copy()
    out["SMA20"] = out["Close"].rolling(20).mean()
    out["SMA50"] = out["Close"].rolling(50).mean()
    out["SMA200"] = out["Close"].rolling(200).mean()
    out["RSI"] = rsi(out["Close"])
    return out
