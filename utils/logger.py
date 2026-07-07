"""앱 전역에서 사용하는 로거. 파일 + 콘솔 동시 출력."""

import logging
import sys

import config


def get_logger(name: str = "gem_finder") -> logging.Logger:
    """이름 기준으로 로거를 생성/재사용한다. 핸들러 중복 부착을 방지한다."""
    logger = logging.getLogger(name)
    if logger.handlers:            # 이미 설정된 로거면 그대로 반환
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # 콘솔 출력
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    logger.addHandler(console)

    # 파일 출력 (logs/ 디렉토리)
    try:
        config.LOG_DIR.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(config.LOG_DIR / "gem_finder.log", encoding="utf-8")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
    except OSError:
        # 파일 로그 실패 시 콘솔만 사용 (앱 동작에는 영향 없음)
        pass

    return logger
