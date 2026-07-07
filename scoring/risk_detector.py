"""
위험 신호 감지기.

점수와 별개로, 사용자가 반드시 알아야 할 경고를 뽑아낸다.
점수가 높아도 위험 신호가 있으면 카드에 함께 표시된다.
"""

from datetime import datetime, timezone
from typing import List, Optional

import config


def detect_risks(fund: Optional[dict], tech: Optional[dict]) -> List[str]:
    """위험 신호 문자열 목록을 반환한다. 없으면 빈 리스트."""
    risks: List[str] = []

    if tech is None:
        return ["데이터 부족"]

    # 최근 20일 급등 → 추격 매수 위험
    ret_20d = tech.get("ret_20d")
    if ret_20d is not None and ret_20d >= config.RISK_SURGE_20D:
        risks.append(f"최근 20일 +{ret_20d * 100:.0f}% 급등 후 과열")

    # RSI 과열
    rsi = tech.get("rsi")
    if rsi is not None and rsi >= config.RSI_OVERBOUGHT:
        risks.append(f"RSI {rsi:.0f} 과열 구간")

    # 거래량 부족
    if (tech.get("volume_avg20") or 0) < config.THIN_VOLUME_SHARES:
        risks.append("거래량 부족")

    # 변동성 과도
    vol = tech.get("volatility")
    if vol is not None and vol >= config.RISK_VOLATILITY_ANNUAL:
        risks.append(f"변동성 높음 (연환산 {vol * 100:.0f}%)")

    if fund is None:
        risks.append("재무 데이터 부족")
        return risks

    # 적자 기업
    if fund.get("net_income") is not None and not fund.get("is_profitable"):
        risks.append("적자 기업")

    # 부채 과다
    dte = fund.get("debt_to_equity")
    if dte is not None and dte > config.DEBT_TO_EQUITY_HIGH:
        risks.append(f"부채비율 높음 ({dte:.0f}%)")

    # 시가총액 과소
    mcap = fund.get("market_cap")
    if mcap is not None and mcap < config.MARKET_CAP_MIN:
        risks.append("시가총액 작음")

    # 실적 발표 임박 (yfinance earningsTimestamp가 있을 때만)
    earnings = fund.get("earnings_date")
    if earnings:
        try:
            ts = datetime.fromtimestamp(int(float(earnings)), tz=timezone.utc)
            days = (ts - datetime.now(timezone.utc)).days
            if 0 <= days <= config.RISK_EARNINGS_DAYS:
                risks.append(f"실적 발표 임박 (D-{days})")
        except (ValueError, OSError, OverflowError):
            pass    # 파싱 불가능한 형식은 무시

    # 핵심 재무 지표가 하나도 없으면 데이터 부족 표시
    if all(fund.get(k) is None for k in ("per", "pbr", "psr")):
        risks.append("밸류에이션 데이터 부족")

    return risks
