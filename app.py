"""
Stock Gem Finder — 메인 Streamlit 앱.

실행: streamlit run app.py

화면 흐름:
  1) 사이드바에서 스캔 규모 선택 → "스캔 시작"
  2) 메인: 히어로 → 지표 타일 → 필터 → 후보 카드 그리드
  3) 카드의 "상세 보기" → 종목 상세 화면 (차트 + 근거 + 지표)
"""

from datetime import date

import pandas as pd
import streamlit as st

import config
from data.market_summary import get_market_summary
from data.price_loader import load_single_price
from db.database import get_latest_scan_date, get_scan_dates, load_scan_results
from indicators.technicals import add_chart_indicators
from scanner import run_scan
from ui.charts import price_volume_rsi_chart
from ui.components import (
    apply_filters, render_detail_header, render_disclaimer, render_filters,
    render_hero, render_metrics_row, render_reason_boxes, render_stat_tiles,
    render_stock_card,
)
from ui.styles import inject_global_styles

st.set_page_config(
    page_title=config.APP_NAME,
    page_icon=config.APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_global_styles()


# ---------------------------------------------------------------------------
# 데이터 로드 헬퍼
# ---------------------------------------------------------------------------

def load_results_df(scan_date: str) -> pd.DataFrame:
    """DB에서 스캔 결과를 불러온다."""
    try:
        return load_scan_results(scan_date)
    except Exception as e:
        st.error(f"스캔 결과를 불러오지 못했습니다: {e}")
        return pd.DataFrame()


def compute_scan_stats(df: pd.DataFrame) -> dict:
    """히어로/타일에 표시할 통계를 계산한다."""
    if df.empty:
        return {"total": 0, "gem_count": 0, "top": None}
    scored = df[df["total_score"].notna()]
    top = scored.iloc[0].to_dict() if len(scored) else None
    return {
        "total": len(df),
        "gem_count": int((scored["total_score"] >= config.GEM_GRADE_MIN).sum()),
        "top": top,
    }


# ---------------------------------------------------------------------------
# 사이드바: 스캔 실행 + 과거 스캔 선택
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown(f"## {config.APP_ICON} {config.APP_NAME}")
    st.caption("저평가 + 단기 모멘텀 후보 발굴 도구")
    st.divider()

    scan_size = st.select_slider(
        "스캔 종목 수 (S&P 500)",
        options=config.SCAN_SIZE_OPTIONS,
        value=config.DEFAULT_SCAN_SIZE,
        help="종목이 많을수록 재무 데이터 수집에 시간이 걸립니다. "
             "전체(503개)는 첫 실행 시 수 분 소요될 수 있습니다.",
    )

    if st.button("🔎 스캔 시작", type="primary", width="stretch"):
        progress_bar = st.progress(0.0, text="준비 중…")

        def _update(msg: str, pct: float):
            progress_bar.progress(min(pct, 1.0), text=msg)

        try:
            run_scan(scan_size=scan_size, progress=_update)
            progress_bar.empty()
            st.success("스캔 완료!")
            st.session_state.pop("selected_ticker", None)
            st.rerun()
        except Exception as e:
            progress_bar.empty()
            st.error(f"스캔 중 오류가 발생했습니다: {e}")

    st.divider()

    # 과거 스캔 날짜 선택 (SQLite에 저장된 이력)
    dates = get_scan_dates()
    if dates:
        selected_date = st.selectbox("스캔 날짜", dates, index=0,
                                     help="과거 스캔 결과를 다시 볼 수 있습니다.")
    else:
        selected_date = None
        st.info("아직 스캔 이력이 없습니다.\n'스캔 시작'을 눌러주세요.")

    st.divider()
    st.caption(config.DISCLAIMER)


# ---------------------------------------------------------------------------
# 메인 영역
# ---------------------------------------------------------------------------

results_df = load_results_df(selected_date) if selected_date else pd.DataFrame()
scan_stats = compute_scan_stats(results_df)

try:
    market = get_market_summary()
except Exception:
    market = {"sentence": "시장 데이터를 불러오지 못했습니다.", "risk_level": "판단 불가"}

# ---- 상세 화면 모드 --------------------------------------------------------
selected = st.session_state.get("selected_ticker")
if selected and not results_df.empty:
    match = results_df[results_df["ticker"] == selected]
    if len(match):
        row = match.iloc[0].to_dict()

        if st.button("← 목록으로 돌아가기"):
            st.session_state.pop("selected_ticker", None)
            st.rerun()

        render_detail_header(row)
        render_reason_boxes(row)

        st.markdown('<div class="section-title">📈 최근 1년 차트</div>',
                    unsafe_allow_html=True)
        price_df = load_single_price(selected)
        if price_df is not None:
            chart_df = add_chart_indicators(price_df)
            st.plotly_chart(price_volume_rsi_chart(chart_df, selected),
                            width="stretch")
        else:
            st.warning("차트 데이터를 불러오지 못했습니다.")

        st.markdown('<div class="section-title">📊 주요 지표</div>',
                    unsafe_allow_html=True)
        render_metrics_row(row)

        render_disclaimer()
        st.stop()
    else:
        st.session_state.pop("selected_ticker", None)

# ---- 대시보드 모드 ----------------------------------------------------------
render_hero(market, scan_stats)
render_stat_tiles(market, scan_stats)

if results_df.empty:
    st.markdown("")
    st.info("👈 사이드바에서 **스캔 시작**을 눌러 오늘의 후보를 찾아보세요. "
            "첫 스캔은 데이터 수집 때문에 1~3분 정도 걸릴 수 있습니다.")
    render_disclaimer()
    st.stop()

# 필터
filters = render_filters(results_df)
filtered = apply_filters(results_df, filters)

# 데이터 부족 종목은 뒤로, 점수순 정렬
filtered = filtered.sort_values(
    "total_score", ascending=False, na_position="last"
).reset_index(drop=True)

st.markdown(
    f'<div class="section-title">✨ 후보 종목 <span style="color:{config.COLORS["text_dim"]};'
    f'font-size:0.85rem;font-weight:400;">{len(filtered)}개 표시 중'
    f' (전체 {len(results_df)}개)</span></div>',
    unsafe_allow_html=True,
)

if filtered.empty:
    st.warning("조건에 맞는 종목이 없습니다. 필터를 완화해보세요.")
else:
    # 3열 카드 그리드
    NUM_COLS = 3
    show_n = st.session_state.get("show_n", 30)
    visible = filtered.head(show_n)

    cols = st.columns(NUM_COLS)
    for i, (_, row) in enumerate(visible.iterrows()):
        with cols[i % NUM_COLS]:
            render_stock_card(row.to_dict(), key=row["ticker"])

    if len(filtered) > show_n:
        if st.button(f"더 보기 ({len(filtered) - show_n}개 남음)"):
            st.session_state.show_n = show_n + 30
            st.rerun()

render_disclaimer()
