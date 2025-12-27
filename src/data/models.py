"""데이터 모델 정의."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class AnalysisRecord:
    """분석 기록."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # 영상 정보
    video_path: str = ""
    video_name: str = ""
    video_duration: float = 0.0
    video_resolution: tuple[int, int] = (0, 0)
    video_size_mb: float = 0.0

    # 추출 설정
    extraction_mode: str = ""  # "all_iframes" | "interval"
    extraction_interval: Optional[float] = None
    frame_count: int = 0

    # AI 분석
    ai_provider: str = ""
    prompt_used: str = ""
    analysis_result: str = ""

    # 메타
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat()
    )

    @property
    def created_datetime(self) -> datetime:
        return datetime.fromisoformat(self.created_at)

    @property
    def interval_description(self) -> str:
        if self.extraction_mode == "all_iframes":
            return "모든 I-Frame"
        elif self.extraction_interval:
            return f"{int(self.extraction_interval)}초 간격"
        return "알 수 없음"


@dataclass
class AppConfig:
    """애플리케이션 설정."""

    # AI 설정
    default_provider: str = "claude"
    output_language: str = "korean"  # 출력 언어 설정

    # 추출 설정
    default_max_dimension: int = 1280
    default_quality: int = 2

    # 캐시 설정
    auto_cleanup: bool = True
    max_cache_size_mb: float = 1024.0  # 1GB
    max_cache_age_days: int = 7

    # 경로 설정
    ffmpeg_path: Optional[str] = None
    ffprobe_path: Optional[str] = None

    @classmethod
    def get_config_path(cls) -> Path:
        return Path.home() / ".movie_file_analyzer" / "config.json"

    @staticmethod
    def get_language_options() -> dict[str, str]:
        """지원 언어 목록과 프롬프트 지시문을 반환합니다."""
        return {
            "korean": "답변은 한국어로 작성해주세요.",
            "english": "Please answer in English.",
            "japanese": "日本語で回答してください。",
            "chinese": "请用中文回答。",
            "auto": "",  # 언어 지시 없음
        }

    @staticmethod
    def get_language_display_names() -> dict[str, str]:
        """UI 표시용 언어 이름을 반환합니다."""
        return {
            "korean": "한국어",
            "english": "English",
            "japanese": "日本語",
            "chinese": "中文",
            "auto": "자동",
        }
