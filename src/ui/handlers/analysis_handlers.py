"""분석 관련 핸들러."""

from datetime import datetime

from PySide6.QtWidgets import QMessageBox

from ...core.ai_connector import AIConnectorFactory, AnalysisResult
from ...core.context_optimizer import AIProvider
from ...core.frame_extractor import VideoInfo
from ...data.models import AnalysisRecord


class AnalysisHandlerMixin:
    """분석 관련 핸들러 믹스인."""

    def _on_provider_changed(self, text: str):
        """AI 제공자 변경."""
        self._update_strategy_list()

    def _on_strategy_changed(self, text: str):
        """추출 전략 변경."""
        if not self.video_info or not text:
            return

        provider = AIProvider.GEMINI
        strategies = self.context_optimizer.get_preset_strategies(
            duration_sec=self.video_info.duration, provider=provider,
        )
        if text in strategies:
            self.current_strategy = strategies[text]

    def _on_analyze_clicked(self):
        """분석 시작 버튼 클릭."""
        if not self.video_path or not self.video_info:
            return

        if self.worker and self.worker.isRunning():
            QMessageBox.warning(
                self, "알림",
                "이전 분석이 진행 중입니다. 완료 후 다시 시도해주세요.",
            )
            return

        if not self.current_strategy:
            provider = AIProvider.GEMINI
            self.current_strategy = self.context_optimizer.calculate_strategy(
                duration_sec=self.video_info.duration, provider=provider,
            )

        provider_name = self.settings_panel.get_provider()
        available = AIConnectorFactory.get_available_providers()
        if provider_name not in available:
            QMessageBox.warning(self, "경고", f"{provider_name} CLI가 설치되어 있지 않습니다.")
            return

        self._start_analysis(provider_name)

    def _start_analysis(self, provider_name: str):
        """분석 워커 시작."""
        from ..worker import AnalysisWorker

        # UI 비활성화
        self.settings_panel.set_analyze_enabled(False)
        self.file_panel.set_browse_enabled(False)
        self.result_panel.set_buttons_enabled(copy=False, save=False)
        self.progress_panel.reset()
        self.result_panel.clear()

        # 워커 시작
        self.worker = AnalysisWorker(
            video_path=self.video_path,
            provider=provider_name,
            strategy=self.current_strategy,
            custom_prompt=self.settings_panel.get_custom_prompt(),
            output_language=self.settings_panel.get_language(),
            model=self.settings_panel.get_model(),
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.frames_ready.connect(self._on_frames_ready)
        self.worker.prompt_ready.connect(self._on_prompt_ready)
        self.worker.ai_analysis_started.connect(self._on_ai_analysis_started)
        self.worker.ai_analysis_finished.connect(self._on_ai_analysis_finished)
        self.worker.finished.connect(self._on_analysis_finished)
        self.worker.error.connect(self._on_analysis_error)
        self.worker.start()

    def _on_progress(self, percent: int, message: str):
        """진행률 업데이트."""
        self.progress_panel.set_progress(percent, message)

    def _on_frames_ready(self, frame_paths: list):
        """프레임 추출 완료."""
        from pathlib import Path
        paths = [Path(p) for p in frame_paths]
        self.result_panel.set_frames(paths)
        self.result_panel.switch_to_tab(1)

    def _on_prompt_ready(self, prompt: str):
        """프롬프트 준비 완료."""
        self.result_panel.set_prompt(prompt)

    def _on_ai_analysis_started(self):
        """AI 분석 시작 시 타이머 시작."""
        self.ai_start_time = datetime.now()
        self.elapsed_timer.start()

    def _on_ai_analysis_finished(self):
        """AI 분석 완료 시 타이머 중지."""
        self.elapsed_timer.stop()
        self.ai_start_time = None

    def _update_elapsed_time(self):
        """AI 분석 중 경과 시간 업데이트."""
        if self.ai_start_time:
            elapsed = datetime.now() - self.ai_start_time
            total_seconds = int(elapsed.total_seconds())
            minutes = total_seconds // 60
            seconds = total_seconds % 60

            time_str = f"{minutes}분 {seconds}초" if minutes > 0 else f"{seconds}초"

            model = self.settings_panel.get_model()
            model_info = f" ({model})" if model != "auto" else ""
            self.progress_panel.set_progress(
                60, f"Gemini{model_info} 분석 중... (경과: {time_str})"
            )

    def _on_analysis_finished(self, result: AnalysisResult, video_info: VideoInfo):
        """분석 완료."""
        self.elapsed_timer.stop()
        self.ai_start_time = None

        self.settings_panel.set_analyze_enabled(True)
        self.file_panel.set_browse_enabled(True)
        self.current_result = result

        if result.success:
            self.result_panel.set_result(result.result)
            self.result_panel.set_buttons_enabled(copy=True, save=True)
            self.result_panel.switch_to_tab(0)

            self._auto_save_to_history()

            if self.cache_manager.auto_cleanup and self.video_path:
                self.cache_manager.cleanup_video_cache(self.video_path)
                self._update_cache_info()
        else:
            self.result_panel.set_result(f"오류: {result.error_message}")
            self.progress_panel.set_progress(100, "❌ 분석 실패")
            self.result_panel.switch_to_tab(0)

    def _auto_save_to_history(self):
        """분석 결과를 자동으로 히스토리에 저장합니다."""
        if not self.current_result or not self.video_path or not self.video_info:
            return

        try:
            record = AnalysisRecord(
                video_path=str(self.video_path),
                video_name=self.video_path.name,
                video_duration=self.video_info.duration,
                video_resolution=self.video_info.resolution,
                video_size_mb=self.video_info.size_mb,
                extraction_mode=self.current_strategy.mode if self.current_strategy else "unknown",
                extraction_interval=self.current_strategy.interval if self.current_strategy else None,
                frame_count=self.current_result.frame_count,
                ai_provider=self.current_result.provider,
                prompt_used=self.current_result.prompt_used,
                analysis_result=self.current_result.result,
            )

            self.metadata_store.save_to_history(record)
            self._load_history()
            self.progress_panel.set_progress(100, "✅ 분석 완료 (히스토리 자동 저장됨)")

        except Exception as e:
            self.progress_panel.set_progress(
                100, f"✅ 분석 완료 (히스토리 저장 실패: {e})"
            )

    def _on_analysis_error(self, error_message: str):
        """분석 오류."""
        self.elapsed_timer.stop()
        self.ai_start_time = None

        self.settings_panel.set_analyze_enabled(True)
        self.file_panel.set_browse_enabled(True)
        self.progress_panel.set_progress(0, "❌ 오류 발생")
        QMessageBox.critical(self, "분석 오류", error_message)

    def _on_save_clicked(self):
        """저장 버튼 클릭."""
        if not self.current_result or not self.video_path or not self.video_info:
            return

        record = AnalysisRecord(
            video_path=str(self.video_path),
            video_name=self.video_path.name,
            video_duration=self.video_info.duration,
            video_resolution=self.video_info.resolution,
            video_size_mb=self.video_info.size_mb,
            extraction_mode=self.current_strategy.mode if self.current_strategy else "unknown",
            extraction_interval=self.current_strategy.interval if self.current_strategy else None,
            frame_count=self.current_result.frame_count,
            ai_provider=self.current_result.provider,
            prompt_used=self.current_result.prompt_used,
            analysis_result=self.current_result.result,
        )

        save_options = self.result_panel.get_save_options()
        results = self.metadata_store.save(
            record=record,
            save_sidecar=save_options["sidecar"],
            save_to_history=True,
            write_to_video=save_options["video_meta"],
        )

        messages = []
        if results.get("sidecar") and not results["sidecar"].startswith("오류"):
            messages.append("✅ 사이드카 저장됨")
        if results.get("history") == "저장됨":
            messages.append("✅ 히스토리 저장됨")
        if results.get("video_metadata") and not results["video_metadata"].startswith("오류"):
            messages.append("✅ 영상 메타데이터 저장됨")

        self.progress_panel.set_progress(100, " | ".join(messages) if messages else "저장 완료")
        self._load_history()
