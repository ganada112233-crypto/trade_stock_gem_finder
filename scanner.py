"""
스캔 파이프라인 (오케스트레이터).

유니버스 → 가격 → 재무 → 지표 → 점수 → 설명 → 위험 → DB 저장
전 과정을 run_scan() 하나로 실행한다.
Streamlit UI와 분리되어 있어서 나중에 크론잡으로도 돌릴 수 있다.
"""

from datetime import date
from typing import Callable, List, Optional

import config
from data.stock_universe import get_universe
from data.price_loader import load_prices
from data.fundamental_loader import load_fundamentals
from db.database import save_scan_results
from indicators.technicals import compute_technicals
from indicators.valuation import sector_medians
from scoring.score_engine import score_stock
from scoring.explanation_generator import generate_explanation
from scoring.risk_detector import detect_risks
from utils.logger import get_logger

log = get_logger(__name__)

# UI 진행 표시용 콜백 타입: (단계 설명, 진행률 0.0~1.0)
ProgressFn = Callable[[str, float], None]


def run_scan(
    scan_size: int = config.DEFAULT_SCAN_SIZE,
    progress: Optional[ProgressFn] = None,
) -> List[dict]:
    """
    S&P 500 상위 scan_size개 종목을 스캔하고 결과를 DB에 저장한다.
    반환: 종목별 결과 딕셔너리 리스트 (점수 내림차순).
    """
    def report(msg: str, pct: float):
        if progress:
            progress(msg, pct)

    # 1) 종목 유니버스
    report("종목 리스트 불러오는 중…", 0.02)
    universe = get_universe()
    targets = universe.head(scan_size)
    tickers = targets["ticker"].tolist()
    meta = targets.set_index("ticker")[["name", "sector"]].to_dict("index")

    # 2) 가격 데이터 (배치 다운로드)
    report(f"{len(tickers)}개 종목 주가 다운로드 중…", 0.10)
    prices = load_prices(tickers)
    latest_prices = {
        t: float(df["Close"].dropna().iloc[-1])
        for t, df in prices.items()
        if df is not None and not df.empty and df["Close"].dropna().size
    }

    # 3) 재무 데이터 (병렬 수집, 진행률 10%→60%)
    def fund_progress(done: int, total: int):
        report(f"재무 데이터 수집 중… ({done}/{total})", 0.10 + 0.50 * done / max(total, 1))

    fundamentals = load_fundamentals(
        tickers,
        progress_callback=fund_progress,
        prices=latest_prices,
    )

    # 4) 기술적 지표
    report("기술적 지표 계산 중…", 0.65)
    technicals = {t: compute_technicals(df) for t, df in prices.items()}

    # 5) 섹터별 밸류에이션 중앙값 (상대 비교용)
    sectors = {t: meta[t]["sector"] for t in tickers if t in meta}
    medians = sector_medians(fundamentals, sectors)

    # 6) 점수 → 설명 → 위험
    report("점수 계산 중…", 0.80)
    results: List[dict] = []
    for t in tickers:
        tech = technicals.get(t)
        fund = fundamentals.get(t)
        sector = meta.get(t, {}).get("sector", "기타")

        score = score_stock(fund, tech, medians.get(sector))
        explanation = generate_explanation(score, fund, tech, sector)
        risks = detect_risks(fund, tech)

        results.append({
            "ticker": t,
            "name": meta.get(t, {}).get("name", t),
            "sector": sector,
            "price": tech.get("price") if tech else None,
            "change_pct": tech.get("change_pct") if tech else None,
            "total_score": score["total"],
            "valuation_score": score["valuation"],
            "momentum_score": score["momentum"],
            "grade": score["grade"],
            "summary": explanation["summary"],
            "explanation": explanation,
            "risks": risks,
            "indicators": tech or {},
            "fundamentals": fund or {},
        })

    # 점수 내림차순 정렬 (데이터 부족은 맨 뒤)
    results.sort(key=lambda r: r["total_score"] if r["total_score"] is not None else -1,
                 reverse=True)

    # 7) DB 저장
    report("결과 저장 중…", 0.95)
    save_scan_results(date.today().isoformat(), results)
    report("완료", 1.0)
    log.info("스캔 완료: %d개 종목", len(results))
    return results
