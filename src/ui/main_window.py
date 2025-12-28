"""메인 윈도우 UI."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .panels import FileSelectionPanel, HistoryPanel, ProgressPanel, ResultPanel, SettingsPanel
from .worker import AnalysisWorker
from .download_worker import DownloadWorker
from ..core.ai_connector import AIConnectorFactory, AnalysisResult
from ..core.youtube_downloader import YouTubeDownloader
from ..core.context_optimizer import AIProvider, ContextOptimizer, ExtractionStrategy
from ..core.frame_extractor import FrameExtractor, VideoInfo
from ..data.metadata_store import MetadataStore
from ..data.models import AnalysisRecord
from ..utils.cache_manager import CacheManager


class MainWindow(QMainWindow):
    """메인 윈도우."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Movie File Analyzer")
        self.setMinimumSize(900, 700)

        self.video_path: Optional[Path] = None
        self.video_info: Optional[VideoInfo] = None
        self.current_strategy: Optional[ExtractionStrategy] = None
        self.current_result: Optional[AnalysisResult] = None
        self.worker: Optional[AnalysisWorker] = None
        self.download_worker: Optional[DownloadWorker] = None

        # 경과 시간 타이머
        self.ai_start_time: Optional[datetime] = None
        self.elapsed_timer = QTimer()
        self.elapsed_timer.setInterval(1000)  # 1초마다
        self.elapsed_timer.timeout.connect(self._update_elapsed_time)

        self.frame_extractor = FrameExtractor()
        self.context_optimizer = ContextOptimizer()
        self.cache_manager = CacheManager()
        self.metadata_store = MetadataStore()

        self._setup_ui()
        self._connect_signals()
        self._update_provider_list()
        self._load_history()

    def _setup_ui(self):
        """UI 구성."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 왼쪽: 메인 패널 (분석)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # 상단: 파일 선택 + 설정
        top_layout = QHBoxLayout()
        self.file_panel = FileSelectionPanel()
        top_layout.addWidget(self.file_panel, 2)

        self.settings_panel = SettingsPanel()
        top_layout.addWidget(self.settings_panel, 1)
        left_layout.addLayout(top_layout)

        # 진행 상황 패널
        self.progress_panel = ProgressPanel()
        left_layout.addWidget(self.progress_panel)

        # 결과 패널
        self.result_panel = ResultPanel()
        self._update_cache_info()
        left_layout.addWidget(self.result_panel, 1)

        # 오른쪽: 히스토리 패널
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.history_panel = HistoryPanel()
        right_layout.addWidget(self.history_panel)

        # 스플리터로 좌우 패널 구성
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([600, 300])
        main_layout.addWidget(splitter)

    def _connect_signals(self):
        """시그널 연결."""
        # 파일 선택 패널
        self.file_panel.file_dropped.connect(self._load_video)
        self.file_panel.browse_clicked.connect(self._on_browse_clicked)
        self.file_panel.youtube_download_clicked.connect(self._on_youtube_download_clicked)

        # 설정 패널
        self.settings_panel.provider_changed.connect(self._on_provider_changed)
        self.settings_panel.strategy_changed.connect(self._on_strategy_changed)
        self.settings_panel.analyze_clicked.connect(self._on_analyze_clicked)

        # 결과 패널
        self.result_panel.copy_clicked.connect(self._on_copy_clicked)
        self.result_panel.save_clicked.connect(self._on_save_clicked)
        self.result_panel.clear_cache_clicked.connect(self._on_clear_cache_clicked)

        # 히스토리 패널
        self.history_panel.item_clicked.connect(self._on_history_item_clicked)
        self.history_panel.refresh_clicked.connect(self._load_history)
        self.history_panel.delete_clicked.connect(self._on_delete_history_clicked)

    def _update_provider_list(self):
        """사용 가능한 AI 제공자 목록을 업데이트합니다 (Gemini 전용)."""
        self.settings_panel.provider_combo.clear()
        available = AIConnectorFactory.get_available_providers()

        if "gemini" in available:
            self.settings_panel.provider_combo.addItem("Gemini ✓")
        else:
            self.settings_panel.provider_combo.addItem("Gemini (설치 필요)")
            QMessageBox.warning(
                self, "경고",
                "Gemini CLI가 설치되어 있지 않습니다.\n"
                "run.sh --install 명령으로 설치하거나\n"
                "npm install -g @google/gemini-cli 명령을 실행하세요.",
            )

    def _update_strategy_list(self):
        """추출 전략 목록을 업데이트합니다."""
        self.settings_panel.strategy_combo.clear()
        if not self.video_info:
            return

        # Gemini 전용
        provider = AIProvider.GEMINI

        strategies = self.context_optimizer.get_preset_strategies(
            duration_sec=self.video_info.duration, provider=provider,
        )

        if "자동 (추천)" in strategies:
            self.settings_panel.strategy_combo.addItem("자동 (추천)")
        for name in strategies:
            if name != "자동 (추천)":
                self.settings_panel.strategy_combo.addItem(name)

    def _load_history(self):
        """히스토리를 로드합니다."""
        self.history_panel.clear()

        try:
            records = self.metadata_store.list_history(limit=50)

            if not records:
                # 히스토리가 비어있는 경우
                self.history_panel.show_empty()
                return

            for record in records:
                date_str = record.created_at[:10] if record.created_at else "unknown"
                text = f"📹 {record.video_name}\n   {date_str} | {record.ai_provider} | {record.frame_count}장"
                self.history_panel.add_item(text, record.id)

            self.history_panel.show_list()

        except PermissionError as e:
            self.history_panel.show_error(f"파일 접근 권한이 없습니다: {e}")
        except (OSError, IOError) as e:
            self.history_panel.show_error(f"파일 시스템 오류: {e}")
        except Exception as e:
            self.history_panel.show_error(f"알 수 없는 오류: {e}")

    def _on_browse_clicked(self):
        """파일 선택 버튼 클릭."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "영상 파일 선택", "",
            "영상 파일 (*.mp4 *.mkv *.avi *.mov *.webm);;모든 파일 (*)",
        )
        if file_path:
            self._load_video(Path(file_path))

    def _load_video(self, video_path: Path):
        """영상 파일을 로드합니다."""
        try:
            self.video_info = self.frame_extractor.get_video_info(video_path)
            self.video_path = video_path

            self.file_panel.set_video_info(
                video_path,
                self.video_info.duration_str,
                self.video_info.width,
                self.video_info.height,
                self.video_info.size_mb,
            )

            self._update_strategy_list()
            self.settings_panel.set_analyze_enabled(True)

            # 기존 분석 결과 확인
            if self.metadata_store.has_sidecar(video_path):
                existing = self.metadata_store.load_sidecar(video_path)
                if existing:
                    reply = QMessageBox.question(
                        self, "기존 분석 결과",
                        f"이 영상의 분석 결과가 이미 있습니다.\n"
                        f"({existing.created_at[:10]}, {existing.ai_provider})\n\n"
                        "기존 결과를 불러오시겠습니까?",
                        QMessageBox.Yes | QMessageBox.No,
                    )
                    if reply == QMessageBox.Yes:
                        self.result_panel.set_result(existing.analysis_result)
                        self.result_panel.set_buttons_enabled(copy=True)

        except Exception as e:
            QMessageBox.critical(self, "오류", f"영상을 로드할 수 없습니다:\n{e}")

    def _on_provider_changed(self, text: str):
        self._update_strategy_list()

    def _on_strategy_changed(self, text: str):
        if not self.video_info or not text:
            return

        # Gemini 전용
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

        # 버그 수정: 이전 워커가 실행 중이면 새 분석 차단
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(
                self, "알림",
                "이전 분석이 진행 중입니다. 완료 후 다시 시도해주세요.",
            )
            return

        if not self.current_strategy:
            # Gemini 전용
            provider = AIProvider.GEMINI

            self.current_strategy = self.context_optimizer.calculate_strategy(
                duration_sec=self.video_info.duration, provider=provider,
            )

        provider_name = self.settings_panel.get_provider()
        available = AIConnectorFactory.get_available_providers()
        if provider_name not in available:
            QMessageBox.warning(self, "경고", f"{provider_name} CLI가 설치되어 있지 않습니다.")
            return

        # UI 비활성화
        self.settings_panel.set_analyze_enabled(False)
        self.file_panel.set_browse_enabled(False)
        self.result_panel.set_buttons_enabled(copy=False, save=False)
        self.progress_panel.reset()
        self.result_panel.clear()

        # 워커 시작 (모델 선택 포함)
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
        self.progress_panel.set_progress(percent, message)

    def _on_frames_ready(self, frame_paths: list):
        paths = [Path(p) for p in frame_paths]
        self.result_panel.set_frames(paths)
        self.result_panel.switch_to_tab(1)

    def _on_prompt_ready(self, prompt: str):
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

            if minutes > 0:
                time_str = f"{minutes}분 {seconds}초"
            else:
                time_str = f"{seconds}초"

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

            # 분석 완료 시 자동으로 히스토리에 저장
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
            # 자동 저장 실패 시 사용자에게 알림 (분석 결과는 유지)
            self.progress_panel.set_progress(
                100, f"✅ 분석 완료 (히스토리 저장 실패: {e})"
            )

    def _on_analysis_error(self, error_message: str):
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

    def _on_copy_clicked(self):
        text = self.result_panel.get_result_text()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            self.progress_panel.set_progress(100, "📋 클립보드에 복사됨")

    def _on_clear_cache_clicked(self):
        reply = QMessageBox.question(
            self, "캐시 정리", "모든 캐시를 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            count = self.cache_manager.cleanup_all()
            self._update_cache_info()
            self.progress_panel.set_progress(100, f"🗑️ {count}개 캐시 삭제됨")

    def _update_cache_info(self):
        cache_size = self.cache_manager.get_total_size()
        cache_size_str = self.cache_manager.format_size(cache_size)
        self.result_panel.set_cache_info(cache_size_str)

    def _on_history_item_clicked(self, item: QListWidgetItem):
        record_id = item.data(Qt.UserRole)
        record = self.metadata_store.get_from_history(record_id)
        if record:
            self.result_panel.set_result(record.analysis_result)
            self.result_panel.set_buttons_enabled(copy=True)
            self.progress_panel.set_progress(
                100, f"📚 히스토리에서 로드: {record.video_name} ({record.created_at[:10]})"
            )

    def _on_delete_history_clicked(self):
        record_id = self.history_panel.get_selected_record_id()
        if record_id is None:
            QMessageBox.information(self, "알림", "삭제할 항목을 선택하세요.")
            return

        reply = QMessageBox.question(
            self, "삭제 확인", "선택한 분석 기록을 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.metadata_store.delete_from_history(record_id)
            self._load_history()
            self.progress_panel.set_progress(100, "🗑️ 히스토리 삭제됨")

    # =========================================================================
    # YouTube 다운로드 처리
    # =========================================================================

    def _on_youtube_download_clicked(self, url: str):
        """YouTube 다운로드 버튼 클릭."""
        # URL 유효성 검사
        if not YouTubeDownloader.is_youtube_url(url):
            QMessageBox.warning(
                self, "잘못된 URL",
                "유효한 YouTube URL이 아닙니다.\n"
                "예: https://youtube.com/watch?v=... 또는 https://youtu.be/...",
            )
            return

        # yt-dlp 설치 확인
        if not YouTubeDownloader.is_available():
            QMessageBox.warning(
                self, "yt-dlp 미설치",
                "yt-dlp가 설치되어 있지 않습니다.\n\n"
                "설치 방법:\n"
                "  • run.sh에서 📦 의존성 관리 메뉴 이용\n"
                "  • pip install --user yt-dlp\n"
                "  • brew install yt-dlp",
            )
            return

        # 이미 다운로드 중인지 확인
        if self.download_worker and self.download_worker.isRunning():
            QMessageBox.warning(self, "알림", "다운로드가 이미 진행 중입니다.")
            return

        # UI 비활성화
        self.file_panel.set_youtube_enabled(False)
        self.file_panel.set_browse_enabled(False)
        self.settings_panel.set_analyze_enabled(False)
        self.progress_panel.reset()
        self.progress_panel.set_progress(0, "📥 YouTube 다운로드 준비 중...")

        # 다운로드 시작
        self.download_worker = DownloadWorker(url)
        self.download_worker.progress.connect(self._on_download_progress)
        self.download_worker.finished.connect(self._on_download_finished)
        self.download_worker.error.connect(self._on_download_error)
        self.download_worker.start()

    def _on_download_progress(self, percent: float, message: str):
        """다운로드 진행률 업데이트."""
        self.progress_panel.set_progress(int(percent * 0.9), message)  # 90%까지

    def _on_download_finished(self, success: bool, file_path: Path, title: str):
        """다운로드 완료."""
        self.file_panel.set_youtube_enabled(True)
        self.file_panel.set_browse_enabled(True)

        if success and file_path and file_path.exists():
            self.progress_panel.set_progress(95, f"✅ 다운로드 완료: {title}")
            self.file_panel.clear_youtube_url()

            # 다운로드된 파일 자동 로드
            self._load_video(file_path)
        else:
            self.progress_panel.set_progress(0, "❌ 다운로드 실패")

    def _on_download_error(self, error_message: str):
        """다운로드 에러."""
        self.file_panel.set_youtube_enabled(True)
        self.file_panel.set_browse_enabled(True)
        self.progress_panel.set_progress(0, "❌ 다운로드 오류")
        QMessageBox.critical(self, "다운로드 오류", error_message)
