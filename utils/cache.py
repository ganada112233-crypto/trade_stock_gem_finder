"""
간단한 파일 기반 캐시.

yfinance 호출을 줄이기 위해 pickle로 결과를 저장하고,
지정한 유효 시간(TTL)이 지나면 자동으로 무효화한다.
Streamlit의 st.cache_data와 별개로, 앱 재시작 후에도 유지되는 캐시다.
"""

import pickle
import time
from pathlib import Path
from typing import Any, Optional

import config
from utils.logger import get_logger

log = get_logger(__name__)


def _cache_path(key: str) -> Path:
    """캐시 키를 안전한 파일명으로 변환한다."""
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in key)
    return config.CACHE_DIR / f"{safe}.pkl"


def cache_get(key: str, ttl_seconds: float) -> Optional[Any]:
    """캐시에서 값을 읽는다. 없거나 만료됐으면 None."""
    path = _cache_path(key)
    if not path.exists():
        return None
    try:
        if time.time() - path.stat().st_mtime > ttl_seconds:
            return None                     # 만료
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception as e:                  # 손상된 캐시는 무시하고 새로 받는다
        log.warning("캐시 읽기 실패 (%s): %s", key, e)
        return None


def cache_set(key: str, value: Any) -> None:
    """값을 캐시에 저장한다. 실패해도 앱은 계속 동작한다."""
    try:
        config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(_cache_path(key), "wb") as f:
            pickle.dump(value, f)
    except Exception as e:
        log.warning("캐시 저장 실패 (%s): %s", key, e)
