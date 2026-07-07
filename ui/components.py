"""
UI 컴포넌트.

히어로, 지표 타일, 필터, 종목 카드, 상세 화면 등
app.py에서 조립해 쓰는 화면 조각들을 모아둔다.
모든 시각 요소는 ui/styles.py의 CSS 클래스를 사용한다.
"""

import html
from datetime import date
from typing import Optional

import pandas as pd
import streamlit as st

import config

_GRADE_BADGE_CLASS = {
    "High Conviction": "grade-gold",
    "Gem Candidate": "grade-purple",
    "Watchlist": "grade-mint",
    "Early Signal": "grade-dim",
    "Low Priority": "grade-dim",
    "데이터 부족": "grade-dim",
}

_WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]


def _esc(text) -> str:
    """HTML 주입 방지용 이스케이프."""
    return html.escape(str(text)) if text is not None else ""


# ---------------------------------------------------------------------------
# 히어로 영역
# ---------------------------------------------------------------------------

def render_hero(market: dict, scan_stats: dict) -> None:
    """상단 히어로: 제목, 날짜, 시장 요약 문장."""
    today = date.today()
    date_str = f"{today.year}년 {today.month}월 {today.day}일 ({_WEEKDAY_KR[today.weekday()]})"

    gem_count = scan_stats.get("gem_count", 0)
    scan_line = ""
    if scan_stats.get("total", 0) > 0:
        scan_line = (f"오늘 {scan_stats['total']}개 종목을 스캔해 "
                     f"관찰 가치가 있는 후보 {gem_count}개를 발견했습니다.")

    st.markdown(f"""
<div class="gem-hero">
  <h1>💎 Today's Stock Gems</h1>
  <div class="hero-date">{date_str} · 미국 주식 단타 후보 스캐너</div>
  <div class="hero-summary">
    {_esc(market.get('sentence', ''))}<br>
    {_esc(scan_line)}
  </div>
</div>
""", unsafe_allow_html=True)


def render_stat_tiles(market: dict, scan_stats: dict) -> None:
    """스캔 수 · Gem 수 · 최고 점수 종목 · 시장 위험도 타일 4개."""
    cols = st.columns(4)

    top = scan_stats.get("top")     # 최고 점수 행 (dict or None)
    top_value = f"{_esc(top['ticker'])} · {top['total_score']:.0f}점" if top else "—"
    top_sub = _esc(top["name"]) if top else "스캔을 실행하세요"

    risk = market.get("risk_level", "판단 불가")
    risk_class = {"안정": "mint", "보통": "gold", "경계": "rose"}.get(risk, "")
    vix = market.get("vix")
    vix_sub = f"VIX {vix:.1f}" if vix is not None else "VIX 데이터 없음"

    tiles = [
        ("스캔 종목", f"{scan_stats.get('total', 0)}개", "S&P 500 유니버스", ""),
        ("Gem 후보", f"{scan_stats.get('gem_count', 0)}개",
         f"{config.GEM_GRADE_MIN}점 이상 (Gem Candidate+)", "gold"),
        ("오늘의 최고점", top_value, top_sub, "gold"),
        ("시장 위험도", risk, vix_sub, risk_class),
    ]
    for col, (label, value, sub, vclass) in zip(cols, tiles):
        with col:
            st.markdown(f"""
<div class="stat-tile">
  <div class="label">{label}</div>
  <div class="value {vclass}">{value}</div>
  <div class="sub">{sub}</div>
</div>
""", unsafe_allow_html=True)


def render_disclaimer() -> None:
    """투자 책임 고지 문구."""
    st.markdown(f'<div class="disclaimer">⚠️ {config.DISCLAIMER}</div>',
                unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 필터
# ---------------------------------------------------------------------------

def render_filters(df: pd.DataFrame) -> dict:
    """필터 UI를 그리고 선택값 딕셔너리를 반환한다."""
    sectors = sorted(df["sector"].dropna().unique().tolist()) if len(df) else []
    grades = [g for _, g in config.GRADE_CUTOFFS]

    with st.expander("🔍 필터", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            price_range = st.slider("주가 범위 ($)", 0, 2000, (0, 2000), step=10)
            min_score = st.slider("최소 총점", 0, 100, 0, step=5)
            sel_sectors = st.multiselect("섹터", sectors)
        with c2:
            per_range = st.slider("PER 범위", 0, 100, (0, 100), step=1)
            rsi_range = st.slider("RSI 범위", 0, 100, (0, 100), step=1)
            min_mcap = st.select_slider(
                "최소 시가총액", options=[0, 2, 10, 50, 200, 500],
                format_func=lambda b: "제한 없음" if b == 0 else f"${b}B+",
            )
        with c3:
            sel_grades = st.multiselect("후보 등급", grades)
            min_volume = st.number_input("최소 20일 평균 거래량 (주)", 0, value=0, step=100_000)
            hide_risky = st.checkbox("위험 신호 있는 종목 숨기기")

    return {
        "price_range": price_range, "min_score": min_score, "sectors": sel_sectors,
        "per_range": per_range, "rsi_range": rsi_range, "min_mcap": min_mcap * 1e9,
        "grades": sel_grades, "min_volume": min_volume, "hide_risky": hide_risky,
    }


def apply_filters(df: pd.DataFrame, f: dict) -> pd.DataFrame:
    """필터 딕셔너리를 DataFrame에 적용한다. 결측치는 관대하게 통과시킨다."""
    if df.empty:
        return df
    out = df.copy()

    def _ind(row, key):
        return (row.get("indicators") or {}).get(key) if isinstance(row.get("indicators"), dict) else None

    def _fund(row, key):
        return (row.get("fundamentals") or {}).get(key) if isinstance(row.get("fundamentals"), dict) else None

    lo, hi = f["price_range"]
    out = out[out["price"].isna() | out["price"].between(lo, hi if hi < 2000 else 1e9)]

    if f["min_score"] > 0:
        out = out[out["total_score"].fillna(-1) >= f["min_score"]]
    if f["sectors"]:
        out = out[out["sector"].isin(f["sectors"])]
    if f["grades"]:
        out = out[out["grade"].isin(f["grades"])]

    plo, phi = f["per_range"]
    if (plo, phi) != (0, 100):
        per = out.apply(lambda r: _fund(r, "per"), axis=1)
        out = out[per.isna() | per.between(plo, phi)]

    rlo, rhi = f["rsi_range"]
    if (rlo, rhi) != (0, 100):
        rsi = out.apply(lambda r: _ind(r, "rsi"), axis=1)
        out = out[rsi.isna() | rsi.between(rlo, rhi)]

    if f["min_mcap"] > 0:
        mcap = out.apply(lambda r: _fund(r, "market_cap"), axis=1)
        out = out[mcap.notna() & (mcap >= f["min_mcap"])]

    if f["min_volume"] > 0:
        vol = out.apply(lambda r: _ind(r, "volume_avg20"), axis=1)
        out = out[vol.notna() & (vol >= f["min_volume"])]

    if f["hide_risky"]:
        out = out[out["risks"].apply(lambda r: not r)]

    return out


# ---------------------------------------------------------------------------
# 종목 카드
# ---------------------------------------------------------------------------

def _score_class(total: Optional[float]) -> str:
    """총점에 따라 카드 점수 색을 결정한다."""
    if total is None:
        return "low"
    if total >= config.GEM_GRADE_MIN:
        return ""           # 골드
    if total >= 60:
        return "mid"        # 퍼플
    return "low"


def render_stock_card(row: dict, key: str) -> None:
    """
    종목 카드 하나를 그린다. '상세 보기' 버튼을 누르면
    st.session_state.selected_ticker에 티커를 저장한다.
    """
    total = row.get("total_score")
    grade = row.get("grade", "")
    change = row.get("change_pct")
    price = row.get("price")
    risks = row.get("risks") or []

    change_cls = "up" if (change or 0) >= 0 else "down"
    change_txt = f"{change:+.2f}%" if change is not None else "—"
    price_txt = f"${price:,.2f}" if price is not None else "—"
    total_txt = f"{total:.0f}" if total is not None else "—"
    top_cls = "top-tier" if (total or 0) >= config.GEM_GRADE_MIN else ""
    bar_pct = min(100, max(0, total or 0))

    badge_cls = _GRADE_BADGE_CLASS.get(grade, "grade-dim")
    risk_badges = "".join(
        f'<span class="badge risk">⚠ {_esc(r)}</span>' for r in risks[:2]
    )
    if len(risks) > 2:
        risk_badges += f'<span class="badge risk">+{len(risks) - 2}</span>'

    st.markdown(f"""
<div class="gem-card {top_cls}">
  <div style="display:flex; justify-content:space-between; align-items:flex-start;">
    <div style="min-width:0;">
      <div class="card-ticker">{_esc(row['ticker'])}</div>
      <div class="card-name">{_esc(row.get('name', ''))}</div>
      <div class="card-sector">{_esc(row.get('sector', ''))}</div>
    </div>
    <div style="flex-shrink:0; margin-left:0.5rem;">
      <div class="card-price">{price_txt}</div>
      <div class="card-change {change_cls}">{change_txt}</div>
    </div>
  </div>
  <div class="card-score-row">
    <span class="card-total {_score_class(total)}">{total_txt}</span>
    <span class="card-breakdown">저평가 {row.get('valuation_score') or 0:.0f} · 모멘텀 {row.get('momentum_score') or 0:.0f}</span>
  </div>
  <div class="score-bar"><div class="fill" style="width:{bar_pct}%"></div></div>
  <div>
    <span class="badge {badge_cls}">{_esc(grade)}</span>
    {risk_badges}
  </div>
  <div class="card-summary">{_esc(row.get('summary', ''))}</div>
</div>
""", unsafe_allow_html=True)

    if st.button("상세 보기", key=f"detail_{key}"):
        st.session_state.selected_ticker = row["ticker"]
        st.rerun()


# ---------------------------------------------------------------------------
# 상세 화면
# ---------------------------------------------------------------------------

def render_detail_header(row: dict) -> None:
    """상세 화면 상단: 종목 정보 + 점수 + 등급 + 위험 배지."""
    total = row.get("total_score")
    grade = row.get("grade", "")
    badge_cls = _GRADE_BADGE_CLASS.get(grade, "grade-dim")
    price = row.get("price")
    change = row.get("change_pct")
    change_cls = "up" if (change or 0) >= 0 else "down"

    risk_badges = "".join(
        f'<span class="badge risk">⚠ {_esc(r)}</span>' for r in (row.get("risks") or [])
    )

    st.markdown(f"""
<div class="detail-header">
  <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:1rem;">
    <div>
      <div style="font-size:1.7rem; font-weight:800;">{_esc(row['ticker'])}
        <span style="font-size:1rem; font-weight:400; color:{config.COLORS['text_dim']};">
          {_esc(row.get('name', ''))} · {_esc(row.get('sector', ''))}</span>
      </div>
      <div style="margin-top:0.5rem;">
        <span class="badge {badge_cls}">{_esc(grade)}</span>{risk_badges}
      </div>
    </div>
    <div style="text-align:right;">
      <div style="font-size:1.6rem; font-weight:700;">{f"${price:,.2f}" if price is not None else "—"}
        <span class="card-change {change_cls}" style="font-size:1rem;">
          {f"{change:+.2f}%" if change is not None else ""}</span>
      </div>
      <div style="font-size:1.05rem; color:{config.COLORS['gold_bright']}; margin-top:0.3rem;">
        총점 {f"{total:.0f}" if total is not None else "—"} / 100
        <span style="color:{config.COLORS['text_dim']}; font-size:0.85rem;">
          (저평가 {row.get('valuation_score') or 0:.0f} · 모멘텀 {row.get('momentum_score') or 0:.0f})</span>
      </div>
    </div>
  </div>
  <div class="hero-summary" style="margin-top:1rem;">{_esc(row.get('summary', ''))}</div>
</div>
""", unsafe_allow_html=True)


def render_reason_boxes(row: dict) -> None:
    """저평가 근거 / 모멘텀 근거 / 주의할 점 3단 박스."""
    exp = row.get("explanation") or {}
    risks = row.get("risks") or []

    def _items(lines):
        return "".join(f"<li>{_esc(s)}</li>" for s in lines) or "<li>해당 없음</li>"

    c1, c2, c3 = st.columns(3)
    boxes = [
        (c1, "val", "💰 저평가 근거", exp.get("valuation", [])),
        (c2, "mom", "⚡ 단타 모멘텀 근거", exp.get("momentum", [])),
        (c3, "risk", "⚠️ 주의할 점", risks or ["특별한 위험 신호가 없습니다."]),
    ]
    for col, cls, title, lines in boxes:
        with col:
            st.markdown(f"""
<div class="reason-box">
  <h4 class="{cls}">{title}</h4>
  <ul>{_items(lines)}</ul>
</div>
""", unsafe_allow_html=True)


def render_metrics_row(row: dict) -> None:
    """PER/PBR/PSR/수익률/부채/배당 지표 타일."""
    fund = row.get("fundamentals") or {}
    ind = row.get("indicators") or {}

    def fmt(v, suffix="", pct=False, digits=1):
        if v is None:
            return "—"
        return f"{v * 100:.{digits}f}%" if pct else f"{v:.{digits}f}{suffix}"

    mcap = fund.get("market_cap")
    mcap_txt = f"${mcap / 1e9:,.0f}B" if mcap else "—"

    metrics = [
        ("PER", fmt(fund.get("per"))),
        ("PBR", fmt(fund.get("pbr"))),
        ("PSR", fmt(fund.get("psr"))),
        ("시가총액", mcap_txt),
        ("매출 성장률", fmt(fund.get("revenue_growth"), pct=True)),
        ("부채비율", fmt(fund.get("debt_to_equity"), suffix="%", digits=0)),
        ("RSI", fmt(ind.get("rsi"), digits=0)),
        ("5일 수익률", fmt(ind.get("ret_5d"), pct=True)),
        ("20일 수익률", fmt(ind.get("ret_20d"), pct=True)),
        ("거래량 배율", fmt(ind.get("volume_ratio"), suffix="×")),
    ]
    cols = st.columns(5)
    for i, (label, value) in enumerate(metrics):
        with cols[i % 5]:
            st.markdown(f"""
<div class="stat-tile" style="margin-bottom:0.8rem; padding:0.8rem 1rem;">
  <div class="label">{label}</div>
  <div class="value" style="font-size:1.15rem;">{value}</div>
</div>
""", unsafe_allow_html=True)
