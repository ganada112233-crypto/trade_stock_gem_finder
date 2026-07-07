# 💎 Stock Gem Finder

미국 주식 시장에서 **저평가 + 단기 모멘텀** 신호가 겹치는 종목을 매일 발굴하는
프리미엄 다크 테마 대시보드입니다.

> ⚠️ 이 앱은 **자동매매 도구가 아닙니다.** 매수/매도 주문 기능이 없으며,
> 모든 결과는 "관찰 후보"일 뿐입니다. 투자 판단과 책임은 사용자 본인에게 있습니다.

![개념](https://img.shields.io/badge/universe-S%26P%20500-7C5CFF)
![스택](https://img.shields.io/badge/stack-Streamlit%20%2B%20yfinance%20%2B%20Plotly-D4AF6A)

## 설치

```bash
cd stock_gem_finder
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 실행

```bash
streamlit run app.py
```

브라우저에서 http://localhost:8501 이 열립니다.

1. 사이드바에서 **스캔 종목 수**를 고르고 (처음엔 30~50개 추천)
2. **🔎 스캔 시작**을 누르면 데이터 수집 → 점수 계산 → 저장까지 자동 진행
3. 카드 그리드에서 후보를 비교하고, **상세 보기**로 차트와 근거를 확인

첫 스캔은 재무 데이터 수집 때문에 종목 수에 따라 1~5분 걸립니다.
가격(1시간)·재무(24시간) 캐시가 있어 재스캔은 훨씬 빠릅니다.

## 점수 체계 (100점 만점)

| 축 | 만점 | 주요 기준 |
|---|---|---|
| 💰 저평가 | 50 | PER/PBR/PSR 절대 수준, **섹터 중앙값 대비 할인**, 매출 성장, 흑자, 배당 / 부채·유동성 감점 |
| ⚡ 단타 모멘텀 | 50 | 거래량 급증(1.5×/2×), RSI 과매도 반등, 20일선 돌파, 골든크로스, 급락 후 반등 / 과열·저유동 감점 |

**등급**: 90+ High Conviction · 80+ Gem Candidate · 70+ Watchlist · 60+ Early Signal

점수와 별개로 과열, 거래량 부족, 적자, 부채 과다, 변동성 과도, 실적 발표 임박 등
**위험 배지**가 함께 표시됩니다. 모든 임계값은 [config.py](config.py)에서 조정합니다.

## 폴더 구조

```
stock_gem_finder/
├── app.py                  # Streamlit 메인 앱
├── scanner.py              # 스캔 파이프라인 (UI와 분리 → 크론잡 가능)
├── config.py               # 모든 설정·임계값·색상
├── data/
│   ├── stock_universe.py   # S&P 500 리스트 (확장 지점: NASDAQ 등)
│   ├── price_loader.py     # 1년치 OHLCV 배치 다운로드
│   ├── fundamental_loader.py # PER/PBR/PSR 등 병렬 수집
│   └── market_summary.py   # 지수·VIX 기반 시장 요약
├── indicators/
│   ├── technicals.py       # RSI, 이동평균, 거래량, 변동성
│   └── valuation.py        # 섹터별 밸류에이션 중앙값
├── scoring/
│   ├── score_engine.py     # 저평가 50 + 모멘텀 50 점수
│   ├── explanation_generator.py # 한국어 자연어 설명
│   └── risk_detector.py    # 위험 신호 감지
├── db/database.py          # SQLite 스캔 이력 저장
├── ui/                     # 스타일 · 컴포넌트 · Plotly 차트
└── utils/                  # 로거 · 파일 캐시 · 데이터 검증
```

## 데이터 · 안전장치

- 데이터 출처: [yfinance](https://github.com/ranaroussi/yfinance) (무료, 지연 시세)
- S&P 500 목록: 위키피디아 (실패 시 내장 폴백 60종목)
- 결측치·상장폐지·네트워크 오류는 종목 단위로 격리 — 한 종목이 실패해도 스캔은 계속됩니다
- 데이터가 부족한 종목은 점수를 계산하지 않고 **"데이터 부족"** 으로 표시
- 스캔 결과는 `gem_finder.db`(SQLite)에 날짜별로 저장 → 사이드바에서 과거 스캔 조회 가능

## 향후 확장 아이디어

구조상 붙이기 쉬운 순서로:

- **유니버스 확장**: `data/stock_universe.py`의 `get_universe()`에 NASDAQ/Russell 추가
- **자동 스캔**: `scanner.run_scan()`을 cron에서 직접 호출 (UI 불필요)
- **어제 후보 성과 추적**: `db.scans` 테이블에 날짜별 가격이 이미 저장됨
- 뉴스 감성 분석, 실적 캘린더, SEC 공시, 관심종목, 알림, 백테스트

## 면책

본 소프트웨어는 교육·정보 제공 목적입니다. 어떤 결과도 투자 권유가 아니며,
데이터 지연·오류 가능성이 있습니다. 투자 손실에 대한 책임은 사용자에게 있습니다.
