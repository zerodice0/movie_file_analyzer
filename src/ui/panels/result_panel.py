"""분석 결과 패널."""

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..widgets import FrameGallery
from .storage_panel import StoragePanel


class ResultPanel(QGroupBox):
    """분석 결과, 프레임, 프롬프트, 저장소 탭과 저장 옵션 패널."""

    copy_clicked = Signal()
    save_clicked = Signal()
    clear_cache_clicked = Signal()
    # 저장소 패널 시그널
    open_download_clicked = Signal()
    open_cache_clicked = Signal()
    cleanup_download_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__("분석 결과", parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 탭 위젯
        self.result_tabs = QTabWidget()

        # 탭 1: 분석 결과
        result_tab = QWidget()
        result_tab_layout = QVBoxLayout(result_tab)
        result_tab_layout.setContentsMargins(4, 4, 4, 4)
        self.result_text = QTextEdit()
        self.result_text.setPlaceholderText("분석 결과가 여기에 표시됩니다...")
        self.result_text.setReadOnly(True)
        result_tab_layout.addWidget(self.result_text)
        self.result_tabs.addTab(result_tab, "📝 분석 결과")

        # 탭 2: 추출된 프레임
        frames_tab = QWidget()
        frames_tab_layout = QVBoxLayout(frames_tab)
        frames_tab_layout.setContentsMargins(4, 4, 4, 4)
        self.frame_gallery = FrameGallery()
        frames_tab_layout.addWidget(self.frame_gallery)
        self.result_tabs.addTab(frames_tab, "🖼️ 추출된 프레임")

        # 탭 3: 사용된 프롬프트
        prompt_tab = QWidget()
        prompt_tab_layout = QVBoxLayout(prompt_tab)
        prompt_tab_layout.setContentsMargins(4, 4, 4, 4)
        self.prompt_text = QTextEdit()
        self.prompt_text.setPlaceholderText("사용된 프롬프트가 여기에 표시됩니다...")
        self.prompt_text.setReadOnly(True)
        prompt_tab_layout.addWidget(self.prompt_text)
        self.result_tabs.addTab(prompt_tab, "💬 프롬프트")

        # 탭 4: 저장소 정보
        self.storage_panel = StoragePanel()
        self.storage_panel.open_download_clicked.connect(self.open_download_clicked.emit)
        self.storage_panel.open_cache_clicked.connect(self.open_cache_clicked.emit)
        self.storage_panel.cleanup_download_clicked.connect(self.cleanup_download_clicked.emit)
        self.storage_panel.cleanup_cache_clicked.connect(self.clear_cache_clicked.emit)
        self.result_tabs.addTab(self.storage_panel, "💾 저장소")

        layout.addWidget(self.result_tabs)

        # 결과 버튼들
        self._setup_buttons(layout)

    def _setup_buttons(self, layout):
        """버튼 영역 설정."""
        btn_layout = QHBoxLayout()

        self.copy_btn = QPushButton("📋 복사")
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self.copy_clicked.emit)
        btn_layout.addWidget(self.copy_btn)

        self.save_btn = QPushButton("💾 저장")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_clicked.emit)
        btn_layout.addWidget(self.save_btn)

        # 저장 옵션
        self.save_sidecar_check = QCheckBox("사이드카")
        self.save_sidecar_check.setChecked(True)
        self.save_sidecar_check.setToolTip("영상 파일 옆에 .analysis.json 저장")
        btn_layout.addWidget(self.save_sidecar_check)

        self.save_video_meta_check = QCheckBox("영상 메타")
        self.save_video_meta_check.setToolTip("영상 파일 내부 메타데이터에 저장 (MKV 권장)")
        btn_layout.addWidget(self.save_video_meta_check)

        btn_layout.addStretch()

        self.clear_cache_btn = QPushButton("🗑️ 캐시 정리")
        self.clear_cache_btn.clicked.connect(self.clear_cache_clicked.emit)
        btn_layout.addWidget(self.clear_cache_btn)

        self.cache_info_label = QLabel("캐시: 0 B")
        btn_layout.addWidget(self.cache_info_label)

        layout.addLayout(btn_layout)

    def set_result(self, text: str):
        """분석 결과 텍스트 설정 (마크다운 렌더링)."""
        self.result_text.setMarkdown(text)

    def set_prompt(self, text: str):
        """프롬프트 텍스트 설정."""
        self.prompt_text.setPlainText(text)

    def set_frames(self, frame_paths: list[Path]):
        """프레임 갤러리에 프레임 설정."""
        self.frame_gallery.set_frames(frame_paths)

    def get_result_text(self) -> str:
        """분석 결과 텍스트 반환."""
        return self.result_text.toPlainText()

    def get_save_options(self) -> dict:
        """저장 옵션 반환."""
        return {
            "sidecar": self.save_sidecar_check.isChecked(),
            "video_meta": self.save_video_meta_check.isChecked(),
        }

    def set_buttons_enabled(self, copy: bool = False, save: bool = False):
        """복사/저장 버튼 활성화 상태 설정."""
        self.copy_btn.setEnabled(copy)
        self.save_btn.setEnabled(save)

    def set_cache_info(self, size_str: str):
        """캐시 정보 레이블 업데이트."""
        self.cache_info_label.setText(f"캐시: {size_str}")

    def switch_to_tab(self, index: int):
        """특정 탭으로 전환."""
        self.result_tabs.setCurrentIndex(index)

    def clear(self):
        """결과 패널 초기화."""
        self.result_text.clear()
        self.prompt_text.clear()
        self.frame_gallery.clear()

    def update_storage_info(
        self,
        download_path: Path,
        download_size: str,
        download_count: int,
        cache_path: Path,
        cache_size: str,
        cache_count: int,
        total_size: str,
    ):
        """저장소 정보 업데이트."""
        self.storage_panel.update_download_info(download_path, download_size, download_count)
        self.storage_panel.update_cache_info(cache_path, cache_size, cache_count)
        self.storage_panel.update_total(total_size)
