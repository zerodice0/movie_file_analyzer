"""백그라운드 분석 작업 스레드."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal

from ..core.ai_connector import AIConnectorFactory, AnalysisResult
from ..core.context_optimizer import ExtractionStrategy
from ..core.frame_extractor import FrameExtractor, VideoInfo
from ..utils.cache_manager import CacheManager


class AnalysisWorker(QThread):
    """백그라운드 분석 작업 스레드."""

    progress = Signal(int, str)  # 진행률(%), 메시지
    frames_ready = Signal(list)  # 추출된 프레임 경로 목록
    prompt_ready = Signal(str)  # 사용된 프롬프트
    ai_analysis_started = Signal()  # AI 분석 시작
    ai_analysis_finished = Signal()  # AI 분석 완료
    finished = Signal(object, object)  # AnalysisResult, VideoInfo
    error = Signal(str)  # 에러 메시지

    def __init__(
        self,
        video_path: Path,
        provider: str,
        strategy: ExtractionStrategy,
        custom_prompt: Optional[str] = None,
        output_language: str = "korean",
        model: str = "auto",
    ):
        super().__init__()
        self.video_path = video_path
        self.provider = provider
        self.strategy = strategy
        self.custom_prompt = custom_prompt
        self.output_language = output_language
        self.model = model

        self.frame_extractor = FrameExtractor()
        self.cache_manager = CacheManager()
        self.video_info: Optional[VideoInfo] = None

    def run(self):
        try:
            # 1. 캐시 디렉토리 생성
            self.progress.emit(5, "캐시 디렉토리 생성 중...")
            frames_dir = self.cache_manager.create_cache_dir(self.video_path)

            # 2. 영상 정보 조회
            self.progress.emit(10, "영상 정보 조회 중...")
            self.video_info = self.frame_extractor.get_video_info(self.video_path)

            # 3. 프레임 추출
            self.progress.emit(20, "프레임 추출 중...")
            frames = self.frame_extractor.extract_frames(
                video_path=self.video_path,
                output_dir=frames_dir,
                interval=self.strategy.interval,
            )
            self.progress.emit(50, f"프레임 {len(frames)}개 추출 완료")

            # 프레임 추출 완료 시그널
            self.frames_ready.emit([str(f) for f in frames])

            # 4. 프롬프트 생성 및 AI 분석
            self.progress.emit(55, "프롬프트 생성 중...")
            connector = AIConnectorFactory.create(self.provider, model=self.model)
            prompt = connector.build_prompt(
                interval_sec=self.strategy.interval,
                frame_count=len(frames),
                duration_str=self.video_info.duration_str,
                custom_prompt=self.custom_prompt,
                output_language=self.output_language,
            )
            self.prompt_ready.emit(prompt)

            # 모델 정보 표시
            model_info = f" ({self.model})" if self.model != "auto" else ""
            self.progress.emit(60, f"Gemini{model_info} 분석 중... (프레임 {len(frames)}개)")

            # AI 분석 시작 시그널
            self.ai_analysis_started.emit()

            result = connector.analyze(
                frame_paths=frames,
                interval_sec=self.strategy.interval,
                duration_str=self.video_info.duration_str,
                custom_prompt=self.custom_prompt,
                output_language=self.output_language,
                working_dir=frames_dir,  # 세션 격리를 위해 캐시 디렉토리에서 실행
            )

            # AI 분석 완료 시그널
            self.ai_analysis_finished.emit()

            # 5. 완료
            self.progress.emit(100, "분석 완료")
            self.finished.emit(result, self.video_info)

        except Exception as e:
            self.ai_analysis_finished.emit()  # 에러 시에도 타이머 중지
            self.error.emit(str(e))
