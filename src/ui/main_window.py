"""메인 윈도우 UI."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .panels import FileSelectionPanel, HistoryPanel, ProgressPanel, ResultPanel, SettingsPanel
from .worker import AnalysisWorker
from .download_worker import DownloadWorker
from .handlers import AnalysisHandlerMixin, VideoHandlerMixin, YouTubeHandlerMixin
from ..core.ai_connector import AIConnectorFactory, AnalysisResult
from ..core.context_optimizer import AIProvider, ContextOptimizer, ExtractionStrategy
from ..core.frame_extractor import FrameExtractor, VideoInfo
from ..data.metadata_store import MetadataStore
from ..utils.cache_manager import CacheManager
from ..utils.storage_manager import StorageManager


class MainWindow(
    VideoHandlerMixin,
    AnalysisHandlerMixin,
    YouTubeHandlerMixin,
    QMainWindow,
):
    """메인 윈도우."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Movie File Analyzer")
        self.setMinimumSize(900, 700)

        self._init_state()
        self._init_services()
        self._setup_ui()
        self._connect_signals()
        self._update_provider_list()
        self._load_history()

    def _init_state(self):
        """상태 변수 초기화."""
        self.video_path: Optional[Path] = None
        self.video_info: Optional[VideoInfo] = None
        self.current_strategy: Optional[ExtractionStrategy] = None
        self.current_result: Optional[AnalysisResult] = None
        self.worker: Optional[AnalysisWorker] = None
        self.download_worker: Optional[DownloadWorker] = None

        # 경과 시간 타이머
        self.ai_start_time: Optional[datetime] = None
        self.elapsed_timer = QTimer()
        self.elapsed_timer.setInterval(1000)
        self.elapsed_timer.timeout.connect(self._update_elapsed_time)

    def _init_services(self):
        """서비스 객체 초기화."""
        self.frame_extractor = FrameExtractor()
        self.context_optimizer = ContextOptimizer()
        self.cache_manager = CacheManager()
        self.metadata_store = MetadataStore()
        self.storage_manager = StorageManager()

    def _setup_ui(self):
        """UI 구성."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # 왼쪽: 메인 패널 (분석)
        left_panel = self._create_left_panel()

        # 오른쪽: 히스토리 패널
        right_panel = self._create_right_panel()

        # 스플리터로 좌우 패널 구성
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([600, 300])
        main_layout.addWidget(splitter)

    def _create_left_panel(self) -> QWidget:
        """왼쪽 패널 생성."""
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
        self._update_storage_info()
        left_layout.addWidget(self.result_panel, 1)

        return left_panel

    def _create_right_panel(self) -> QWidget:
        """오른쪽 패널 생성."""
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.history_panel = HistoryPanel()
        right_layout.addWidget(self.history_panel)
        return right_panel

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
        # 저장소 패널
        self.result_panel.open_download_clicked.connect(self._on_open_download_clicked)
        self.result_panel.open_cache_clicked.connect(self._on_open_cache_clicked)
        self.result_panel.cleanup_download_clicked.connect(self._on_cleanup_download_clicked)

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

        provider = AIProvider.GEMINI
        strategies = self.context_optimizer.get_preset_strategies(
            duration_sec=self.video_info.duration, provider=provider,
        )

        if "자동 (추천)" in strategies:
            self.settings_panel.strategy_combo.addItem("자동 (추천)")
        for name in strategies:
            if name != "자동 (추천)":
                self.settings_panel.strategy_combo.addItem(name)
