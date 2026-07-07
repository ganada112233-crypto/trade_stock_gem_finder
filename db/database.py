"""
SQLite 저장소.

매일 스캔 결과를 scans 테이블에 저장한다.
(scan_date, ticker)가 유니크 키라서 같은 날 재스캔하면 덮어쓴다.
나중에 "어제 후보가 오늘 어떻게 움직였는지" 비교하는 기능의 기반이 된다.
"""

import json
import sqlite3
from contextlib import contextmanager
from typing import List, Optional

import pandas as pd

import config
from utils.logger import get_logger

log = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_date       TEXT NOT NULL,          -- YYYY-MM-DD
    ticker          TEXT NOT NULL,
    name            TEXT,
    sector          TEXT,
    price           REAL,
    change_pct      REAL,
    total_score     REAL,
    valuation_score REAL,
    momentum_score  REAL,
    grade           TEXT,
    summary         TEXT,                   -- 카드용 한 줄 설명
    explanation     TEXT,                   -- 상세 설명 JSON
    risks           TEXT,                   -- 위험 신호 JSON 배열
    indicators      TEXT,                   -- 주요 지표 JSON
    fundamentals    TEXT,                   -- 재무 스냅샷 JSON
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(scan_date, ticker)
);
CREATE INDEX IF NOT EXISTS idx_scans_date ON scans(scan_date);
"""


@contextmanager
def _connect():
    """스키마가 보장된 커넥션을 여닫는 컨텍스트 매니저."""
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, timeout=30)
    try:
        conn.execute("PRAGMA busy_timeout = 30000")
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_scan_results(scan_date: str, rows: List[dict]) -> int:
    """
    스캔 결과 리스트를 저장한다. 같은 날짜+티커는 덮어쓴다(UPSERT).
    저장된 행 수를 반환한다.
    """
    if not rows:
        return 0
    with _connect() as conn:
        # 같은 날 재스캔 시 이전 실행 결과를 완전히 대체한다
        conn.execute("DELETE FROM scans WHERE scan_date = ?", (scan_date,))
        for r in rows:
            conn.execute(
                """
                INSERT INTO scans (scan_date, ticker, name, sector, price, change_pct,
                                   total_score, valuation_score, momentum_score, grade,
                                   summary, explanation, risks, indicators, fundamentals)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(scan_date, ticker) DO UPDATE SET
                    price=excluded.price, change_pct=excluded.change_pct,
                    total_score=excluded.total_score,
                    valuation_score=excluded.valuation_score,
                    momentum_score=excluded.momentum_score,
                    grade=excluded.grade, summary=excluded.summary,
                    explanation=excluded.explanation, risks=excluded.risks,
                    indicators=excluded.indicators, fundamentals=excluded.fundamentals
                """,
                (
                    scan_date, r["ticker"], r.get("name"), r.get("sector"),
                    r.get("price"), r.get("change_pct"),
                    r.get("total_score"), r.get("valuation_score"),
                    r.get("momentum_score"), r.get("grade"),
                    r.get("summary"),
                    json.dumps(r.get("explanation", {}), ensure_ascii=False),
                    json.dumps(r.get("risks", []), ensure_ascii=False),
                    json.dumps(r.get("indicators", {}), ensure_ascii=False),
                    json.dumps(r.get("fundamentals", {}), ensure_ascii=False),
                ),
            )
    log.info("스캔 결과 %d건 저장 (%s)", len(rows), scan_date)
    return len(rows)


def load_scan_results(scan_date: str) -> pd.DataFrame:
    """특정 날짜의 스캔 결과를 DataFrame으로 불러온다."""
    with _connect() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM scans WHERE scan_date = ? ORDER BY total_score DESC",
            conn, params=(scan_date,),
        )
    # JSON 컬럼 복원
    for col in ("explanation", "risks", "indicators", "fundamentals"):
        if col in df.columns:
            df[col] = df[col].apply(lambda x: json.loads(x) if x else None)
    return df


def get_scan_dates() -> List[str]:
    """저장된 스캔 날짜 목록 (최신순)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT scan_date FROM scans ORDER BY scan_date DESC"
        ).fetchall()
    return [r[0] for r in rows]


def get_latest_scan_date() -> Optional[str]:
    """가장 최근 스캔 날짜. 없으면 None."""
    dates = get_scan_dates()
    return dates[0] if dates else None
