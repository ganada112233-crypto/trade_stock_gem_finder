"""
점수 엔진.

총점(100) = 저평가 점수(50) + 단타 모멘텀 점수(50)

모든 기준값은 config.py에 있다. 각 항목이 왜 점수를 받았는지
reasons 리스트에 기록해서 설명 생성기가 사용할 수 있게 한다.
"""

from typing import Dict, List, Optional, Tuple

import config
from indicators.valuation import relative_to_sector


def _grade(total: float) -> str:
    """총점 → 후보 등급."""
    for cutoff, label in config.GRADE_CUTOFFS:
        if total >= cutoff:
            return label
    return config.GRADE_CUTOFFS[-1][1]


def valuation_score(fund: Optional[dict], tech: Optional[dict],
                    sector_median: Optional[dict]) -> Tuple[float, List[str]]:
    """
    저평가 점수 (0~50)와 근거 태그 목록을 반환한다.
    근거 태그는 explanation_generator가 한국어 문장으로 변환한다.
    """
    if fund is None:
        return 0.0, ["no_fundamentals"]

    score = 0.0
    reasons: List[str] = []
    P = config.VAL_POINTS

    per, pbr, psr = fund.get("per"), fund.get("pbr"), fund.get("psr")

    # --- PER (구간별 가점) -------------------------------------------------
    if per is not None:
        if per <= config.PER_GOOD:
            score += P["per_low"]
            reasons.append("per_good")
        elif per <= config.PER_OK:
            score += P["per_low"] * 0.5
            reasons.append("per_ok")

    # --- PBR ---------------------------------------------------------------
    if pbr is not None:
        if pbr <= config.PBR_GOOD:
            score += P["pbr_low"]
            reasons.append("pbr_good")
        elif pbr <= config.PBR_OK:
            score += P["pbr_low"] * 0.5
            reasons.append("pbr_ok")

    # --- PSR ---------------------------------------------------------------
    if psr is not None:
        if psr <= config.PSR_GOOD:
            score += P["psr_low"]
            reasons.append("psr_good")
        elif psr <= config.PSR_OK:
            score += P["psr_low"] * 0.5
            reasons.append("psr_ok")

    # --- 섹터 상대 비교 (PER/PBR/PSR 중 섹터 대비 할인폭이 큰 것 기준) ------
    if sector_median:
        ratios = [
            r for r in (
                relative_to_sector(per, sector_median.get("per")),
                relative_to_sector(pbr, sector_median.get("pbr")),
                relative_to_sector(psr, sector_median.get("psr")),
            ) if r is not None
        ]
        if ratios:
            best = min(ratios)
            if best <= config.SECTOR_DISCOUNT_STRONG:
                score += P["sector_discount"]
                reasons.append("sector_discount_strong")
            elif best <= config.SECTOR_DISCOUNT_MILD:
                score += P["sector_discount"] * 0.5
                reasons.append("sector_discount_mild")

    # --- 성장성 · 수익성 ----------------------------------------------------
    growth = fund.get("revenue_growth")
    if growth is not None and growth > 0:
        score += P["revenue_growth"]
        reasons.append("revenue_growing")

    if fund.get("is_profitable"):
        score += P["profitable"]
        reasons.append("profitable")

    div = fund.get("dividend_yield")
    if div is not None and div > 0:
        score += P["dividend"]
        reasons.append("dividend")

    # --- 감점 ---------------------------------------------------------------
    dte = fund.get("debt_to_equity")
    if dte is not None and dte > config.DEBT_TO_EQUITY_HIGH:
        score += config.VAL_PENALTIES["high_debt"]
        reasons.append("high_debt")

    mcap = fund.get("market_cap")
    adv = tech.get("avg_dollar_volume") if tech else None
    if (mcap is not None and mcap < config.MARKET_CAP_MIN) or \
       (adv is not None and adv < config.AVG_DOLLAR_VOLUME_MIN):
        score += config.VAL_PENALTIES["low_liquidity"]
        reasons.append("low_liquidity")

    return max(0.0, min(config.VALUATION_MAX, score)), reasons


def momentum_score(tech: Optional[dict]) -> Tuple[float, List[str]]:
    """단타 모멘텀 점수 (0~50)와 근거 태그 목록을 반환한다."""
    if tech is None:
        return 0.0, ["no_technicals"]

    score = 0.0
    reasons: List[str] = []
    P = config.MOM_POINTS

    # --- 거래량 급증 ---------------------------------------------------------
    vr = tech.get("volume_ratio") or 0.0
    if vr >= config.VOLUME_SPIKE_1:
        score += P["volume_1_5x"]
        reasons.append("volume_spike")
        if vr >= config.VOLUME_SPIKE_2:
            score += P["volume_2x"]
            reasons.append("volume_spike_big")

    # --- RSI 신호 ------------------------------------------------------------
    rsi = tech.get("rsi")
    rsi_rising = tech.get("rsi_rising", False)
    rsi_min_5d = tech.get("rsi_min_5d")
    if rsi is not None:
        # 과매도(최근 5일 저점이 30 이하) + 현재 반등 중
        oversold_recently = (rsi <= config.RSI_OVERSOLD) or \
                            (rsi_min_5d is not None and rsi_min_5d <= config.RSI_OVERSOLD)
        if oversold_recently and rsi_rising:
            score += P["rsi_oversold_bounce"]
            reasons.append("rsi_oversold_bounce")
        elif config.RSI_MID_LOW <= rsi <= config.RSI_MID_HIGH and rsi_rising:
            score += P["rsi_midrange_turn"]
            reasons.append("rsi_midrange_turn")

    # --- 이동평균 돌파 ---------------------------------------------------------
    if tech.get("cross_sma20"):
        score += P["cross_sma20"]
        reasons.append("cross_sma20")
    if tech.get("golden_cross"):
        score += P["golden_cross"]
        reasons.append("golden_cross")

    # --- 급락 후 반등 -----------------------------------------------------------
    ret_5d = tech.get("ret_5d")
    if ret_5d is not None and ret_5d <= config.DIP_5D_THRESHOLD and \
       (tech.get("green_candle") or (tech.get("change_pct") or 0) > 0):
        score += P["dip_rebound"]
        reasons.append("dip_rebound")

    # --- 감점 --------------------------------------------------------------------
    ret_20d = tech.get("ret_20d")
    if ret_20d is not None and ret_20d >= config.SURGE_20D_THRESHOLD:
        score += config.MOM_PENALTIES["overheated_20d"]
        reasons.append("overheated_20d")

    if rsi is not None and rsi >= config.RSI_OVERBOUGHT:
        score += config.MOM_PENALTIES["rsi_overbought"]
        reasons.append("rsi_overbought")

    if (tech.get("volume_avg20") or 0) < config.THIN_VOLUME_SHARES:
        score += config.MOM_PENALTIES["thin_volume"]
        reasons.append("thin_volume")

    return max(0.0, min(config.MOMENTUM_MAX, score)), reasons


def score_stock(fund: Optional[dict], tech: Optional[dict],
                sector_median: Optional[dict]) -> dict:
    """
    종목 하나의 최종 점수 패키지를 만든다.
    데이터가 부족하면 grade="데이터 부족"으로 표시하고 점수를 계산하지 않는다.
    """
    if tech is None:
        return {
            "total": None, "valuation": None, "momentum": None,
            "grade": "데이터 부족",
            "val_reasons": [], "mom_reasons": ["no_technicals"],
        }

    val, val_reasons = valuation_score(fund, tech, sector_median)
    mom, mom_reasons = momentum_score(tech)
    total = round(val + mom, 1)

    return {
        "total": total,
        "valuation": round(val, 1),
        "momentum": round(mom, 1),
        "grade": _grade(total),
        "val_reasons": val_reasons,
        "mom_reasons": mom_reasons,
    }
