"""
Plotly 차트.

상세 화면용 캔들 + 이동평균 + 거래량 + RSI 3단 차트를 만든다.
- 다크 서페이스에서 색각이상(CVD)·대비 검증을 통과한 팔레트 사용
- 이중 y축 금지 → 패널을 분리한 서브플롯 구성
- 격자선은 은은하게, 데이터 선은 2px
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import config

CC = config.CHART_COLORS
C = config.COLORS

_GRID = "#252B45"
_AXIS_FONT = dict(color=C["text_dim"], size=11)


def _base_layout(fig: go.Figure, height: int) -> None:
    """다크 테마 공통 레이아웃을 적용한다."""
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=C["text"], size=12),
        margin=dict(l=10, r=10, t=36, b=10),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0,
            font=dict(color=C["text_dim"], size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=C["bg_card"], bordercolor=_GRID,
                        font=dict(color=C["text"], size=12)),
        xaxis_rangeslider_visible=False,
    )
    fig.update_xaxes(gridcolor=_GRID, zeroline=False, tickfont=_AXIS_FONT,
                     showspikes=True, spikecolor=C["text_faint"],
                     spikethickness=1, spikedash="dot")
    fig.update_yaxes(gridcolor=_GRID, zeroline=False, tickfont=_AXIS_FONT)


def price_volume_rsi_chart(df: pd.DataFrame, ticker: str) -> go.Figure:
    """
    1년 캔들차트(+SMA 20/50/200) · 거래량 · RSI 3단 차트.
    df는 indicators.technicals.add_chart_indicators()를 거친 DataFrame.
    """
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.58, 0.18, 0.24], vertical_spacing=0.04,
    )

    # --- 1단: 캔들 + 이동평균 ---------------------------------------------
    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name=ticker,
        increasing=dict(line=dict(color=CC["mint"], width=1), fillcolor=CC["mint"]),
        decreasing=dict(line=dict(color=CC["rose"], width=1), fillcolor=CC["rose"]),
    ), row=1, col=1)

    for col, color, dash in (
        ("SMA20", CC["purple"], None),
        ("SMA50", CC["gold"], None),
        ("SMA200", CC["neutral"], "dot"),
    ):
        if col in df.columns and df[col].notna().any():
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col], name=col, mode="lines",
                line=dict(color=color, width=2, dash=dash),
            ), row=1, col=1)

    # --- 2단: 거래량 (단일 색조 = 크기 인코딩) -------------------------------
    fig.add_trace(go.Bar(
        x=df.index, y=df["Volume"], name="거래량",
        marker=dict(color=CC["purple"], opacity=0.45, line_width=0),
    ), row=2, col=1)

    # --- 3단: RSI + 30/70 기준선 --------------------------------------------
    if "RSI" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["RSI"], name="RSI(14)", mode="lines",
            line=dict(color=CC["purple"], width=2),
        ), row=3, col=1)
        for level, label in ((70, "과열 70"), (30, "과매도 30")):
            fig.add_hline(y=level, row=3, col=1, line_width=1, line_dash="dash",
                          line_color=C["text_faint"],
                          annotation_text=label,
                          annotation_font=dict(color=C["text_faint"], size=10),
                          annotation_position="right")
        fig.update_yaxes(range=[0, 100], row=3, col=1)

    _base_layout(fig, height=680)
    fig.update_yaxes(title_text="가격 ($)", title_font=_AXIS_FONT, row=1, col=1)
    fig.update_yaxes(title_text="거래량", title_font=_AXIS_FONT, row=2, col=1)
    fig.update_yaxes(title_text="RSI", title_font=_AXIS_FONT, row=3, col=1)
    return fig
