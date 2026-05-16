# =========================================================
# run_youtube_summary.py
# 위치: D:/project/youtube_summary/run_youtube_summary.py
# 역할:
#   1. 공통 함수 폴더를 import 경로에 추가
#   2. config.yaml 로드
#   3. 환경 및 로그 설정
#   4. YouTubeSummaryPipeline 실행
# =========================================================

import sys
from pathlib import Path


# ---------------------------------------------------------
# 1. 공통 기능 폴더 import 경로 등록
# ---------------------------------------------------------
FUNCTION_DIR = Path("D:/project/function")

if str(FUNCTION_DIR) not in sys.path:
    sys.path.insert(0, str(FUNCTION_DIR))


# ---------------------------------------------------------
# 2. 모듈 import
# ---------------------------------------------------------
from common_utils import CommonManager
from youtube_summary import YouTubeSummaryPipeline


# ---------------------------------------------------------
# 3. 실행 엔트리포인트
# ---------------------------------------------------------
if __name__ == "__main__":
    CONFIG_PATH = "./project/youtube_summary/config.yaml"

    config = CommonManager.load_config(CONFIG_PATH)
    CommonManager.setup_environment(config)

    pipeline = YouTubeSummaryPipeline(config)
    pipeline.run()