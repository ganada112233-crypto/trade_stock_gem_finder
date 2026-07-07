"""
Stock Gem Finder 전역 설정.

점수 기준, 등급 컷오프, 위험 판정 임계값, 색상 테마 등
조정 가능한 모든 값을 이 파일에 모아둔다.
숫자를 바꾸면 스캔/점수/화면에 바로 반영된다.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# 기본 경로
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "gem_finder.db"
CACHE_DIR = BASE_DIR / ".cache"
LOG_DIR = BASE_DIR / "logs"

APP_NAME = "Stock Gem Finder"
APP_ICON = "💎"

# ---------------------------------------------------------------------------
# 종목 유니버스
# ---------------------------------------------------------------------------
UNIVERSE = "SP500"                  # 향후 "NASDAQ100", "RUSSELL2000" 등 확장
SP500_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
UNIVERSE_CACHE_HOURS = 24           # 종목 리스트 캐시 유효 시간

# 스캔 시 한 번에 처리할 종목 수 옵션 (yfinance 속도 고려)
SCAN_SIZE_OPTIONS = [30, 50, 100, 200, 503]
DEFAULT_SCAN_SIZE = 50

PRICE_HISTORY_PERIOD = "1y"         # 최근 1년 주가
PRICE_CACHE_MINUTES = 60            # 가격 데이터 캐시 유효 시간(분)
FUNDAMENTAL_CACHE_HOURS = 24        # 재무 데이터 캐시 유효 시간
PRICE_BATCH_SIZE = 50               # 대량 스캔 시 yfinance 동시 연결 폭 제한
FUNDAMENTAL_MAX_WORKERS = 3         # 재무 데이터 병렬 요청 수 (파일/소켓 고갈 방지)

MIN_HISTORY_DAYS = 60               # 지표 계산에 필요한 최소 거래일 수

# ---------------------------------------------------------------------------
# 저평가 점수 (최대 50점)
# ---------------------------------------------------------------------------
VALUATION_MAX = 50

VAL_POINTS = {
    "per_low": 10,          # PER이 낮을수록 (구간별 가점)
    "pbr_low": 7,           # PBR이 낮을수록
    "psr_low": 7,           # PSR이 낮을수록
    "sector_discount": 10,  # 섹터 평균 대비 저평가
    "revenue_growth": 6,    # 매출 성장률 양수
    "profitable": 6,        # 순이익 흑자
    "dividend": 4,          # 배당 지급
}
VAL_PENALTIES = {
    "high_debt": -6,        # 부채비율 과다
    "low_liquidity": -5,    # 시총·유동성 부족
}

# PER/PBR/PSR 절대 기준 (섹터 데이터 부족 시 사용)
PER_GOOD = 15.0
PER_OK = 25.0
PBR_GOOD = 1.5
PBR_OK = 3.0
PSR_GOOD = 2.0
PSR_OK = 4.0

# 섹터 평균 대비 할인율 기준 (예: 0.8 = 섹터 평균의 80% 이하)
SECTOR_DISCOUNT_STRONG = 0.70
SECTOR_DISCOUNT_MILD = 0.85

DEBT_TO_EQUITY_HIGH = 200.0     # yfinance debtToEquity는 % 단위
MARKET_CAP_MIN = 2e9            # 이보다 작으면 유동성 감점
AVG_DOLLAR_VOLUME_MIN = 5e6     # 일평균 거래대금 최소치($)

# ---------------------------------------------------------------------------
# 단타 모멘텀 점수 (최대 50점)
# ---------------------------------------------------------------------------
MOMENTUM_MAX = 50

MOM_POINTS = {
    "volume_1_5x": 8,        # 거래량 20일 평균의 1.5배 이상
    "volume_2x": 5,          # 2배 이상이면 추가
    "rsi_oversold_bounce": 10,  # RSI 30 이하 과매도 반등
    "rsi_midrange_turn": 6,  # RSI 40~55 상승 전환
    "cross_sma20": 8,        # 주가가 20일선 상향 돌파
    "golden_cross": 8,       # 20일선이 50일선 상향 돌파
    "dip_rebound": 8,        # 최근 5일 급락 후 당일 반등
}
MOM_PENALTIES = {
    "overheated_20d": -8,    # 최근 20일 급등 (추격 위험)
    "rsi_overbought": -8,    # RSI 70 이상 과열
    "thin_volume": -6,       # 거래량 너무 적음
}

VOLUME_SPIKE_1 = 1.5         # 거래량 배수 1차 기준
VOLUME_SPIKE_2 = 2.0         # 거래량 배수 2차 기준
RSI_OVERSOLD = 30.0
RSI_MID_LOW = 40.0
RSI_MID_HIGH = 55.0
RSI_OVERBOUGHT = 70.0
DIP_5D_THRESHOLD = -0.05     # 5일 -5% 이상 하락이면 '급락'
SURGE_20D_THRESHOLD = 0.25   # 20일 +25% 이상이면 '급등(과열)'
THIN_VOLUME_SHARES = 300_000 # 20일 평균 거래량 최소 주수

# ---------------------------------------------------------------------------
# 후보 등급 컷오프
# ---------------------------------------------------------------------------
GRADE_CUTOFFS = [
    (90, "High Conviction"),
    (80, "Gem Candidate"),
    (70, "Watchlist"),
    (60, "Early Signal"),
    (0,  "Low Priority"),
]
GEM_GRADE_MIN = 80           # "Gem Candidate 이상" 판정 기준

# ---------------------------------------------------------------------------
# 위험 신호 임계값
# ---------------------------------------------------------------------------
RISK_SURGE_20D = 0.25            # 20일 급등 과열
RISK_VOLATILITY_ANNUAL = 0.60    # 연환산 변동성 60% 이상
RISK_EARNINGS_DAYS = 7           # 실적 발표 D-7 이내면 경고

# ---------------------------------------------------------------------------
# 시장 위험도 (VIX 대용: SPY 변동성 + 지수 흐름)
# ---------------------------------------------------------------------------
MARKET_INDEX_TICKERS = {"S&P 500": "^GSPC", "NASDAQ": "^IXIC", "VIX": "^VIX"}
VIX_CALM = 15.0
VIX_NERVOUS = 25.0

# ---------------------------------------------------------------------------
# 색상 테마 (다크 · 프리미엄 보석함 컨셉)
# ---------------------------------------------------------------------------
COLORS = {
    "bg": "#0B0E1A",           # 짙은 네이비-차콜 배경
    "bg_card": "#141829",      # 카드 배경
    "bg_card_hover": "#1A1F35",
    "border": "#252B45",
    "purple": "#7C5CFF",       # 딥 퍼플 포인트
    "purple_soft": "#4A3B8C",
    "gold": "#D4AF6A",         # 골드 강조
    "gold_bright": "#E8C87E",
    "mint": "#5FD4B0",         # 긍정 신호 (과하지 않은 민트)
    "rose": "#D97883",         # 위험 신호 (탁한 로즈)
    "text": "#E8EAF2",
    "text_dim": "#8B91A8",
    "text_faint": "#5A6078",
}

# 차트 데이터 시리즈 전용 색 (다크 서페이스 기준 CVD/대비 검증 완료)
CHART_COLORS = {
    "purple": "#7C5CFF",   # 주 시리즈 (RSI, SMA20, 거래량)
    "mint": "#2FA98A",     # 상승 캔들
    "gold": "#B08A36",     # SMA50
    "rose": "#C75D74",     # 하락 캔들
    "neutral": "#8B91A8",  # SMA200 (보조선)
}

GRADE_COLORS = {
    "High Conviction": COLORS["gold"],
    "Gem Candidate": COLORS["purple"],
    "Watchlist": COLORS["mint"],
    "Early Signal": COLORS["text_dim"],
    "Low Priority": COLORS["text_faint"],
}

DISCLAIMER = (
    "본 화면의 모든 종목은 매수 추천이 아닌 **관찰 후보**입니다. "
    "투자 판단과 그에 따른 책임은 전적으로 사용자 본인에게 있습니다."
)
