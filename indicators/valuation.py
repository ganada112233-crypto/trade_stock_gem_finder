"""
밸류에이션 비교 지표.

섹터별로 PER/PBR/PSR 중앙값을 계산해서
"섹터 평균 대비 얼마나 저평가인지"를 판단하는 데 사용한다.
(평균 대신 중앙값을 쓰면 극단값에 휘둘리지 않는다.)
"""

from typing import Dict, Optional

import pandas as pd

_METRICS = ["per", "pbr", "psr"]
_MIN_SAMPLES = 3    # 섹터 내 표본이 이보다 적으면 비교하지 않음


def sector_medians(fundamentals: Dict[str, dict], sectors: Dict[str, str]) -> Dict[str, dict]:
    """
    {섹터명: {"per": 중앙값, "pbr": 중앙값, "psr": 중앙값}} 를 계산한다.
    fundamentals: {티커: 재무 스냅샷}, sectors: {티커: 섹터명}
    """
    rows = []
    for t, f in fundamentals.items():
        sector = sectors.get(t)
        if not sector:
            continue
        rows.append({"sector": sector, **{m: f.get(m) for m in _METRICS}})

    if not rows:
        return {}

    df = pd.DataFrame(rows)
    result: Dict[str, dict] = {}
    for sector, group in df.groupby("sector"):
        medians = {}
        for m in _METRICS:
            values = group[m].dropna()
            medians[m] = float(values.median()) if len(values) >= _MIN_SAMPLES else None
        result[sector] = medians
    return result


def relative_to_sector(value: Optional[float], sector_median: Optional[float]) -> Optional[float]:
    """
    섹터 중앙값 대비 비율을 반환한다. (0.7 = 섹터의 70% 수준 → 저평가)
    비교 불가능하면 None.
    """
    if value is None or sector_median is None or sector_median <= 0:
        return None
    return value / sector_median
