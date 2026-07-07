"""
전역 CSS 스타일.

Streamlit 기본 UI 느낌을 지우고 '프리미엄 금융 앱 + 보석함' 컨셉의
다크 테마를 입힌다. 색상 값은 config.COLORS에서 가져온다.
"""

import streamlit as st

import config

C = config.COLORS


def inject_global_styles() -> None:
    """앱 시작 시 한 번 호출해서 전역 CSS를 주입한다."""
    st.markdown(f"""
<style>
/* ---------- 기본 배경 · 타이포그래피 ---------- */
.stApp {{
    background:
        radial-gradient(ellipse 80% 50% at 20% -10%, rgba(124,92,255,0.10), transparent),
        radial-gradient(ellipse 60% 40% at 90% 0%, rgba(212,175,106,0.05), transparent),
        {C['bg']};
    color: {C['text']};
}}
html, body, [class*="css"] {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Pretendard",
                 "Noto Sans KR", sans-serif;
}}
/* Streamlit 기본 헤더/푸터 숨김 */
header[data-testid="stHeader"] {{ background: transparent; }}
#MainMenu, footer {{ visibility: hidden; }}
.block-container {{ padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1280px; }}

/* ---------- 사이드바 ---------- */
section[data-testid="stSidebar"] {{
    background: {C['bg_card']};
    border-right: 1px solid {C['border']};
}}
section[data-testid="stSidebar"] .block-container {{ padding-top: 1.5rem; }}

/* ---------- 히어로 영역 ---------- */
.gem-hero {{
    background: linear-gradient(135deg, rgba(124,92,255,0.14) 0%,
                rgba(20,24,41,0.9) 45%, rgba(212,175,106,0.07) 100%);
    border: 1px solid {C['border']};
    border-radius: 20px;
    padding: 2.2rem 2.4rem;
    margin-bottom: 1.6rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.35);
}}
.gem-hero h1 {{
    font-size: 2.1rem; font-weight: 700; margin: 0 0 0.3rem 0;
    background: linear-gradient(90deg, {C['text']} 30%, {C['gold_bright']});
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}}
.gem-hero .hero-date {{ color: {C['text_dim']}; font-size: 0.95rem; margin-bottom: 1rem; }}
.gem-hero .hero-summary {{
    color: {C['text']}; font-size: 1.02rem; line-height: 1.6;
    border-left: 3px solid {C['purple']}; padding-left: 0.9rem; margin: 1rem 0 0 0;
}}

/* ---------- 지표 타일 ---------- */
.stat-tile {{
    background: {C['bg_card']};
    border: 1px solid {C['border']};
    border-radius: 14px;
    padding: 1.1rem 1.3rem;
    height: 100%;
}}
.stat-tile .label {{ color: {C['text_dim']}; font-size: 0.8rem; letter-spacing: 0.04em;
                     text-transform: uppercase; margin-bottom: 0.35rem; }}
.stat-tile .value {{ color: {C['text']}; font-size: 1.55rem; font-weight: 700; }}
.stat-tile .sub {{ color: {C['text_faint']}; font-size: 0.82rem; margin-top: 0.2rem; }}
.stat-tile .value.gold {{ color: {C['gold_bright']}; }}
.stat-tile .value.mint {{ color: {C['mint']}; }}
.stat-tile .value.rose {{ color: {C['rose']}; }}

/* ---------- 종목 카드 ---------- */
.gem-card {{
    background: {C['bg_card']};
    border: 1px solid {C['border']};
    border-radius: 16px;
    padding: 1.3rem 1.4rem 1.1rem;
    margin-bottom: 0.4rem;
    transition: border-color 0.2s, transform 0.15s;
    position: relative;
    overflow: hidden;
}}
.gem-card:hover {{ border-color: {C['purple_soft']}; transform: translateY(-2px); }}
.gem-card.top-tier {{
    border: 1px solid rgba(212,175,106,0.45);
    background: linear-gradient(160deg, rgba(212,175,106,0.06), {C['bg_card']} 40%);
}}
.gem-card .card-ticker {{ font-size: 1.25rem; font-weight: 700; color: {C['text']}; }}
.gem-card .card-name {{ color: {C['text_dim']}; font-size: 0.85rem;
                        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.gem-card .card-sector {{ color: {C['text_faint']}; font-size: 0.75rem; margin-top: 0.1rem; }}
.gem-card .card-price {{ font-size: 1.15rem; font-weight: 600; color: {C['text']}; text-align: right; }}
.gem-card .card-change {{ font-size: 0.85rem; text-align: right; }}
.gem-card .card-change.up {{ color: {C['mint']}; }}
.gem-card .card-change.down {{ color: {C['rose']}; }}
.gem-card .card-score-row {{
    display: flex; align-items: baseline; gap: 0.6rem; margin: 0.9rem 0 0.3rem;
}}
.gem-card .card-total {{ font-size: 1.9rem; font-weight: 800; color: {C['gold_bright']}; }}
.gem-card .card-total.mid {{ color: {C['purple']}; }}
.gem-card .card-total.low {{ color: {C['text_dim']}; }}
.gem-card .card-breakdown {{ color: {C['text_dim']}; font-size: 0.8rem; }}
.gem-card .card-summary {{
    color: {C['text']}; font-size: 0.87rem; line-height: 1.5;
    margin-top: 0.55rem; min-height: 2.6em; opacity: 0.9;
}}

/* 점수 게이지 바 */
.score-bar {{ height: 5px; border-radius: 3px; background: {C['border']};
              margin: 0.5rem 0 0.7rem; overflow: hidden; }}
.score-bar .fill {{ height: 100%; border-radius: 3px;
    background: linear-gradient(90deg, {C['purple']}, {C['gold']}); }}

/* ---------- 배지 ---------- */
.badge {{
    display: inline-block; padding: 0.22rem 0.7rem; border-radius: 999px;
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.03em;
    margin-right: 0.35rem; margin-bottom: 0.3rem;
}}
.badge.grade-gold {{ background: rgba(212,175,106,0.15); color: {C['gold_bright']};
                     border: 1px solid rgba(212,175,106,0.4); }}
.badge.grade-purple {{ background: rgba(124,92,255,0.15); color: #A891FF;
                       border: 1px solid rgba(124,92,255,0.4); }}
.badge.grade-mint {{ background: rgba(95,212,176,0.12); color: {C['mint']};
                     border: 1px solid rgba(95,212,176,0.35); }}
.badge.grade-dim {{ background: rgba(139,145,168,0.12); color: {C['text_dim']};
                    border: 1px solid {C['border']}; }}
.badge.risk {{ background: rgba(217,120,131,0.12); color: {C['rose']};
               border: 1px solid rgba(217,120,131,0.35); }}

/* ---------- 버튼 ---------- */
.stButton > button {{
    background: rgba(124,92,255,0.12);
    color: {C['text']};
    border: 1px solid {C['purple_soft']};
    border-radius: 10px;
    font-size: 0.85rem;
    transition: background 0.2s;
    width: 100%;
}}
.stButton > button:hover {{
    background: rgba(124,92,255,0.28);
    border-color: {C['purple']};
    color: {C['text']};
}}
/* 주 액션 버튼 (스캔 시작) */
.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {C['purple']}, {C['purple_soft']});
    border: none; font-weight: 600;
}}
.stButton > button[kind="primary"]:hover {{
    background: linear-gradient(135deg, #8D70FF, {C['purple']});
}}

/* ---------- 구분선 · 섹션 제목 ---------- */
.section-title {{
    font-size: 1.15rem; font-weight: 700; color: {C['text']};
    margin: 1.6rem 0 0.9rem; display: flex; align-items: center; gap: 0.5rem;
}}
.section-title::after {{
    content: ""; flex: 1; height: 1px;
    background: linear-gradient(90deg, {C['border']}, transparent);
}}

/* ---------- 디스클레이머 ---------- */
.disclaimer {{
    background: rgba(217,120,131,0.06);
    border: 1px solid rgba(217,120,131,0.25);
    border-radius: 12px;
    padding: 0.8rem 1.1rem;
    color: {C['text_dim']}; font-size: 0.82rem; line-height: 1.5;
    margin: 1.4rem 0;
}}

/* ---------- 상세 화면 ---------- */
.detail-header {{
    background: {C['bg_card']};
    border: 1px solid {C['border']};
    border-radius: 18px;
    padding: 1.6rem 1.9rem;
    margin-bottom: 1.2rem;
}}
.reason-box {{
    background: {C['bg_card']};
    border: 1px solid {C['border']};
    border-radius: 14px;
    padding: 1.1rem 1.3rem;
    height: 100%;
}}
.reason-box h4 {{ margin: 0 0 0.6rem; font-size: 0.95rem; }}
.reason-box h4.val {{ color: {C['gold_bright']}; }}
.reason-box h4.mom {{ color: #A891FF; }}
.reason-box h4.risk {{ color: {C['rose']}; }}
.reason-box ul {{ margin: 0; padding-left: 1.1rem; color: {C['text']};
                  font-size: 0.87rem; line-height: 1.65; opacity: 0.9; }}

/* ---------- 필터 영역 (expander) ---------- */
div[data-testid="stExpander"] {{
    background: {C['bg_card']};
    border: 1px solid {C['border']} !important;
    border-radius: 14px !important;
}}
div[data-testid="stExpander"] summary {{ color: {C['text']}; }}

/* ---------- 모바일 대응 ---------- */
@media (max-width: 640px) {{
    .gem-hero {{ padding: 1.4rem 1.3rem; }}
    .gem-hero h1 {{ font-size: 1.5rem; }}
    .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
}}
</style>
""", unsafe_allow_html=True)
