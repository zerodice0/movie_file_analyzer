"""UI 패널 컴포넌트 모음."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .widgets import DropZoneFrame, FrameGallery
from ..data.models import AppConfig


class FileSelectionPanel(QWidget):
    """파일 선택 영역 패널 (드래그 앤 드롭 + YouTube URL 지원)."""

    file_dropped = Signal(Path)
    browse_clicked = Signal()
    youtube_download_clicked = Signal(str)  # YouTube URL

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.drop_zone = DropZoneFrame()
        self.drop_zone.file_dropped.connect(self.file_dropped.emit)

        inner_layout = QVBoxLayout(self.drop_zone)
        inner_layout.setContentsMargins(12, 12, 12, 12)

        self.drop_hint_label = QLabel("📁 영상 파일을 여기에 드래그하거나 아래 버튼을 클릭하세요")
        self.drop_hint_label.setAlignment(Qt.AlignCenter)
        self.drop_hint_label.setStyleSheet("color: #666; font-size: 11px;")
        inner_layout.addWidget(self.drop_hint_label)

        file_select_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("영상 파일 경로...")
        self.file_path_edit.setReadOnly(True)
        file_select_layout.addWidget(self.file_path_edit)

        self.browse_btn = QPushButton("📂 찾아보기")
        self.browse_btn.clicked.connect(self.browse_clicked.emit)
        file_select_layout.addWidget(self.browse_btn)
        inner_layout.addLayout(file_select_layout)

        # YouTube URL 입력 영역
        youtube_layout = QHBoxLayout()
        self.youtube_url_edit = QLineEdit()
        self.youtube_url_edit.setPlaceholderText("YouTube URL (예: https://youtube.com/watch?v=...)")
        self.youtube_url_edit.returnPressed.connect(self._on_youtube_download)
        youtube_layout.addWidget(self.youtube_url_edit)

        self.youtube_download_btn = QPushButton("📥 다운로드")
        self.youtube_download_btn.clicked.connect(self._on_youtube_download)
        self.youtube_download_btn.setToolTip("yt-dlp로 YouTube 영상 다운로드")
        youtube_layout.addWidget(self.youtube_download_btn)
        inner_layout.addLayout(youtube_layout)

        self.video_info_label = QLabel("")
        self.video_info_label.setStyleSheet("color: gray;")
        inner_layout.addWidget(self.video_info_label)

        layout.addWidget(self.drop_zone)

    def _on_youtube_download(self):
        """YouTube 다운로드 버튼 클릭 처리."""
        url = self.youtube_url_edit.text().strip()
        if url:
            self.youtube_download_clicked.emit(url)

    def set_video_info(self, path: Path, duration_str: str, width: int, height: int, size_mb: float):
        """영상 정보 표시."""
        self.file_path_edit.setText(str(path))
        self.drop_hint_label.hide()

        info_text = (
            f"📹 {path.name}\n"
            f"⏱️ {duration_str} | "
            f"📐 {width}x{height} | "
            f"💾 {size_mb:.1f}MB"
        )
        self.video_info_label.setText(info_text)
        self.video_info_label.setStyleSheet("color: #333; font-weight: bold;")

        self.drop_zone.setStyleSheet("""
            DropZoneFrame {
                border: 2px solid #4CAF50;
                border-radius: 8px;
                background-color: #f9fff9;
            }
        """)

    def set_browse_enabled(self, enabled: bool):
        """찾아보기 버튼 활성화 상태 설정."""
        self.browse_btn.setEnabled(enabled)

    def set_youtube_enabled(self, enabled: bool):
        """YouTube 다운로드 UI 활성화 상태 설정."""
        self.youtube_url_edit.setEnabled(enabled)
        self.youtube_download_btn.setEnabled(enabled)

    def clear_youtube_url(self):
        """YouTube URL 입력 초기화."""
        self.youtube_url_edit.clear()


class SettingsPanel(QGroupBox):
    """AI 제공자, 모델, 전략, 언어, 커스텀 프롬프트 설정 패널."""

    provider_changed = Signal(str)
    model_changed = Signal(str)
    strategy_changed = Signal(str)
    analyze_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__("설정", parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # AI 제공자 선택 (Gemini 고정)
        provider_layout = QHBoxLayout()
        provider_layout.addWidget(QLabel("AI 제공자:"))
        self.provider_combo = QComboBox()
        self.provider_combo.currentTextChanged.connect(self.provider_changed.emit)
        provider_layout.addWidget(self.provider_combo)
        layout.addLayout(provider_layout)

        # AI 모델 선택
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("AI 모델:"))
        self.model_combo = QComboBox()
        model_options = AppConfig.get_model_options()
        for key, display_name in model_options.items():
            self.model_combo.addItem(display_name, key)
        self.model_combo.currentTextChanged.connect(self.model_changed.emit)
        model_layout.addWidget(self.model_combo)
        layout.addLayout(model_layout)

        # 추출 전략 선택
        strategy_layout = QHBoxLayout()
        strategy_layout.addWidget(QLabel("추출 간격:"))
        self.strategy_combo = QComboBox()
        self.strategy_combo.currentTextChanged.connect(self.strategy_changed.emit)
        strategy_layout.addWidget(self.strategy_combo)
        layout.addLayout(strategy_layout)

        # 출력 언어 선택
        language_layout = QHBoxLayout()
        language_layout.addWidget(QLabel("출력 언어:"))
        self.language_combo = QComboBox()
        language_names = AppConfig.get_language_display_names()
        for key, display_name in language_names.items():
            self.language_combo.addItem(display_name, key)
        language_layout.addWidget(self.language_combo)
        layout.addLayout(language_layout)

        # 커스텀 프롬프트
        layout.addWidget(QLabel("추가 프롬프트 (선택):"))
        self.custom_prompt_edit = QLineEdit()
        self.custom_prompt_edit.setPlaceholderText("예: 기술적인 내용 위주로 설명해주세요")
        layout.addWidget(self.custom_prompt_edit)

        # 분석 시작 버튼
        self.analyze_btn = QPushButton("🚀 분석 시작")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self.analyze_clicked.emit)
        layout.addWidget(self.analyze_btn)

    def get_provider(self) -> str:
        """선택된 제공자 이름 반환 (소문자)."""
        text = self.provider_combo.currentText()
        return text.split()[0].lower() if text else ""

    def get_model(self) -> str:
        """선택된 모델 키 반환."""
        return self.model_combo.currentData() or "auto"

    def get_strategy_name(self) -> str:
        """선택된 전략 이름 반환."""
        return self.strategy_combo.currentText()

    def get_language(self) -> str:
        """선택된 언어 코드 반환."""
        return self.language_combo.currentData()

    def get_custom_prompt(self) -> Optional[str]:
        """커스텀 프롬프트 반환 (없으면 None)."""
        text = self.custom_prompt_edit.text().strip()
        return text if text else None

    def set_analyze_enabled(self, enabled: bool):
        """분석 버튼 활성화 상태 설정."""
        self.analyze_btn.setEnabled(enabled)


class ProgressPanel(QGroupBox):
    """진행 상황 표시 패널."""

    def __init__(self, parent=None):
        super().__init__("진행 상황", parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("대기 중")
        self.progress_label.setStyleSheet("color: gray;")
        layout.addWidget(self.progress_label)

    def set_progress(self, percent: int, message: str):
        """진행률과 메시지 업데이트."""
        self.progress_bar.setValue(percent)
        self.progress_label.setText(message)

    def reset(self):
        """진행 상태 초기화."""
        self.progress_bar.setValue(0)
        self.progress_label.setText("대기 중")


class ResultPanel(QGroupBox):
    """분석 결과, 프레임, 프롬프트 탭과 저장 옵션 패널."""

    copy_clicked = Signal()
    save_clicked = Signal()
    clear_cache_clicked = Signal()

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

        layout.addWidget(self.result_tabs)

        # 결과 버튼들
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


class HistoryPanel(QGroupBox):
    """분석 히스토리 목록 패널."""

    item_clicked = Signal(object)  # QListWidgetItem
    refresh_clicked = Signal()
    delete_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__("📚 분석 히스토리", parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self.item_clicked.emit)
        layout.addWidget(self.history_list)

        btn_layout = QHBoxLayout()

        self.refresh_btn = QPushButton("🔄 새로고침")
        self.refresh_btn.clicked.connect(self.refresh_clicked.emit)
        btn_layout.addWidget(self.refresh_btn)

        self.delete_btn = QPushButton("🗑️ 삭제")
        self.delete_btn.clicked.connect(self.delete_clicked.emit)
        btn_layout.addWidget(self.delete_btn)

        layout.addLayout(btn_layout)

    def clear(self):
        """히스토리 목록 초기화."""
        self.history_list.clear()

    def add_item(self, text: str, record_id: str):
        """히스토리 항목 추가."""
        item = QListWidgetItem()
        item.setText(text)
        item.setData(Qt.UserRole, record_id)
        self.history_list.addItem(item)

    def get_selected_item(self) -> Optional[QListWidgetItem]:
        """선택된 항목 반환."""
        return self.history_list.currentItem()

    def get_selected_record_id(self) -> Optional[str]:
        """선택된 항목의 record_id 반환."""
        item = self.history_list.currentItem()
        if item:
            return item.data(Qt.UserRole)
        return None
