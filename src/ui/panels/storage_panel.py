"""저장소 정보 패널."""

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class StorageSection(QFrame):
    """개별 저장소 섹션 (다운로드/캐시)."""

    open_clicked = Signal()
    cleanup_clicked = Signal()

    def __init__(self, title: str, icon: str, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            StorageSection {
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 8px;
                background-color: #fafafa;
            }
        """)
        self._setup_ui(title, icon)

    def _setup_ui(self, title: str, icon: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # 헤더: 아이콘 + 제목
        header_layout = QHBoxLayout()
        header_label = QLabel(f"{icon} {title}")
        header_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # 경로
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("경로:"))
        self.path_label = QLabel("-")
        self.path_label.setStyleSheet("color: #666;")
        self.path_label.setWordWrap(True)
        path_layout.addWidget(self.path_label, 1)
        layout.addLayout(path_layout)

        # 용량 정보
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel("용량:"))
        self.size_label = QLabel("0 B")
        self.size_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        info_layout.addWidget(self.size_label)
        info_layout.addSpacing(16)

        info_layout.addWidget(QLabel("파일:"))
        self.count_label = QLabel("0개")
        self.count_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        info_layout.addWidget(self.count_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)

        # 버튼들
        btn_layout = QHBoxLayout()
        self.open_btn = QPushButton("📂 폴더 열기")
        self.open_btn.clicked.connect(self.open_clicked.emit)
        btn_layout.addWidget(self.open_btn)

        self.cleanup_btn = QPushButton("🗑️ 정리")
        self.cleanup_btn.clicked.connect(self.cleanup_clicked.emit)
        btn_layout.addWidget(self.cleanup_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def update_info(self, path: Path, size_str: str, file_count: int):
        """저장소 정보 업데이트."""
        # 경로 표시 (홈 디렉토리는 ~로 축약)
        path_str = str(path)
        home = str(Path.home())
        if path_str.startswith(home):
            path_str = "~" + path_str[len(home):]
        self.path_label.setText(path_str)
        self.path_label.setToolTip(str(path))

        self.size_label.setText(size_str)
        self.count_label.setText(f"{file_count}개")


class StoragePanel(QWidget):
    """저장소 정보 패널 (다운로드 + 캐시)."""

    open_download_clicked = Signal()
    open_cache_clicked = Signal()
    cleanup_download_clicked = Signal()
    cleanup_cache_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(16)

        # 설명
        desc_label = QLabel(
            "YouTube에서 다운로드한 영상과 분석용 프레임 캐시의 저장 위치 및 용량입니다."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; margin-bottom: 8px;")
        layout.addWidget(desc_label)

        # 다운로드 섹션
        self.download_section = StorageSection("다운로드", "📥")
        self.download_section.open_clicked.connect(self.open_download_clicked.emit)
        self.download_section.cleanup_clicked.connect(self.cleanup_download_clicked.emit)
        layout.addWidget(self.download_section)

        # 캐시 섹션
        self.cache_section = StorageSection("프레임 캐시", "🗂️")
        self.cache_section.open_clicked.connect(self.open_cache_clicked.emit)
        self.cache_section.cleanup_clicked.connect(self.cleanup_cache_clicked.emit)
        layout.addWidget(self.cache_section)

        # 전체 요약
        summary_frame = QFrame()
        summary_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 8px;
                background-color: #f5f5f5;
            }
        """)
        summary_layout = QHBoxLayout(summary_frame)
        summary_layout.addWidget(QLabel("전체 사용량:"))
        self.total_label = QLabel("0 B")
        self.total_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #333;")
        summary_layout.addWidget(self.total_label)
        summary_layout.addStretch()
        layout.addWidget(summary_frame)

        layout.addStretch()

    def update_download_info(self, path: Path, size_str: str, file_count: int):
        """다운로드 폴더 정보 업데이트."""
        self.download_section.update_info(path, size_str, file_count)

    def update_cache_info(self, path: Path, size_str: str, file_count: int):
        """캐시 폴더 정보 업데이트."""
        self.cache_section.update_info(path, size_str, file_count)

    def update_total(self, total_size_str: str):
        """전체 용량 업데이트."""
        self.total_label.setText(total_size_str)
