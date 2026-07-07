"""
설명 생성기.

점수 엔진이 남긴 근거 태그(reason tag)를 자연스러운 한국어 문장으로 변환한다.
숫자 나열이 아니라 "왜 이 종목이 후보인지"를 사람이 읽을 수 있게 만든다.
"""

from typing import List, Optional


def _valuation_sentences(reasons: List[str], fund: Optional[dict],
                         sector: str) -> List[str]:
    """저평가 근거 문장들."""
    s: List[str] = []
    fund = fund or {}
    per, pbr, psr = fund.get("per"), fund.get("pbr"), fund.get("psr")

    # 섹터 상대 저평가가 가장 강한 신호이므로 먼저
    if "sector_discount_strong" in reasons:
        s.append(f"{sector} 섹터 평균보다 뚜렷하게 저평가되어 있습니다.")
    elif "sector_discount_mild" in reasons:
        s.append(f"{sector} 섹터 평균 대비 다소 저평가된 수준입니다.")

    cheap = [name for tag, name in
             (("per_good", f"PER {per:.1f}" if per else "PER"),
              ("pbr_good", f"PBR {pbr:.1f}" if pbr else "PBR"),
              ("psr_good", f"PSR {psr:.1f}" if psr else "PSR"))
             if tag in reasons]
    if cheap:
        s.append(f"{', '.join(cheap)} 등 절대 밸류에이션도 낮은 편입니다.")

    growth = fund.get("revenue_growth")
    if "revenue_growing" in reasons and growth is not None:
        s.append(f"최근 매출이 {growth * 100:.1f}% 성장 중입니다.")

    if "profitable" in reasons:
        s.append("순이익 흑자를 유지하고 있습니다.")

    if "high_debt" in reasons:
        s.append("다만 부채비율이 높은 점은 감안해야 합니다.")

    if "no_fundamentals" in reasons:
        s.append("재무 데이터가 부족해 저평가 여부를 판단하기 어렵습니다.")

    return s


def _momentum_sentences(reasons: List[str], tech: Optional[dict]) -> List[str]:
    """단타 모멘텀 근거 문장들."""
    s: List[str] = []
    tech = tech or {}
    vr = tech.get("volume_ratio")
    rsi = tech.get("rsi")

    if "volume_spike_big" in reasons and vr:
        s.append(f"최근 거래량이 20일 평균의 {vr:.1f}배로 크게 늘었습니다.")
    elif "volume_spike" in reasons and vr:
        s.append(f"거래량이 20일 평균의 {vr:.1f}배로 증가했습니다.")

    if "rsi_oversold_bounce" in reasons and rsi is not None:
        s.append(f"RSI {rsi:.0f}로 과매도 구간에서 반등 신호가 나오고 있습니다.")
    elif "rsi_midrange_turn" in reasons and rsi is not None:
        s.append(f"RSI가 {rsi:.0f}에서 상승 전환하며 힘이 붙고 있습니다.")

    if "cross_sma20" in reasons:
        s.append("주가가 20일 이동평균선을 상향 돌파했습니다.")
    if "golden_cross" in reasons:
        s.append("20일선이 50일선을 상향 돌파하는 골든크로스가 발생했습니다.")

    ret_5d = tech.get("ret_5d")
    if "dip_rebound" in reasons and ret_5d is not None:
        s.append(f"최근 5일 {ret_5d * 100:.1f}% 하락 후 당일 반등이 나타났습니다.")

    if "overheated_20d" in reasons:
        ret_20d = tech.get("ret_20d")
        pct = f"+{ret_20d * 100:.0f}%" if ret_20d is not None else ""
        s.append(f"다만 최근 20일 {pct} 급등해 단기 추격 위험이 있습니다.")
    if "rsi_overbought" in reasons and rsi is not None:
        s.append(f"RSI {rsi:.0f}로 이미 과열 구간이라 주의가 필요합니다.")

    if "no_technicals" in reasons:
        s.append("주가 데이터가 부족해 모멘텀을 판단할 수 없습니다.")

    return s


def generate_explanation(score: dict, fund: Optional[dict],
                         tech: Optional[dict], sector: str) -> dict:
    """
    {"summary": 카드용 한 줄, "valuation": [...], "momentum": [...]}
    를 반환한다. summary는 가장 강한 근거 1~2개로 만든다.
    """
    val_s = _valuation_sentences(score.get("val_reasons", []), fund, sector)
    mom_s = _momentum_sentences(score.get("mom_reasons", []), tech)

    # 카드에 보여줄 핵심 한 줄: 모멘텀 첫 문장 + 저평가 첫 문장 순으로 조합
    highlights = []
    if mom_s:
        highlights.append(mom_s[0])
    if val_s:
        highlights.append(val_s[0])
    if not highlights:
        highlights.append("뚜렷한 신호가 없어 관찰만 권장되는 종목입니다.")

    return {
        "summary": " ".join(highlights[:2]),
        "valuation": val_s or ["저평가 관련 특이 신호가 없습니다."],
        "momentum": mom_s or ["모멘텀 관련 특이 신호가 없습니다."],
    }
