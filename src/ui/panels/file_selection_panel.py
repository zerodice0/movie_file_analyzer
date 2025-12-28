"""파일 선택 영역 패널."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..widgets import DropZoneFrame


class FileSelectionPanel(QWidget):
    """파일 선택 영역 패널 (드래그 앤 드롭 + YouTube URL 지원)."""

    file_dropped = Signal(Path)
    browse_clicked = Signal()
    youtube_download_clicked = Signal(str)

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
