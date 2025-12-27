"""재사용 가능한 커스텀 위젯 모음."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


# 지원하는 영상 확장자
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".flv"}


class DropZoneFrame(QFrame):
    """드래그 앤 드롭을 지원하는 파일 선택 영역."""

    file_dropped = Signal(Path)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._setup_style()

    def _setup_style(self):
        """기본 스타일 설정."""
        self.setStyleSheet("""
            DropZoneFrame {
                border: 2px dashed #aaa;
                border-radius: 8px;
                background-color: #fafafa;
            }
            DropZoneFrame:hover {
                border-color: #666;
                background-color: #f0f0f0;
            }
        """)

    def _set_drag_hover_style(self, hover: bool):
        """드래그 오버 시 스타일 변경."""
        if hover:
            self.setStyleSheet("""
                DropZoneFrame {
                    border: 2px dashed #4CAF50;
                    border-radius: 8px;
                    background-color: #e8f5e9;
                }
            """)
        else:
            self._setup_style()

    def dragEnterEvent(self, event: QDragEnterEvent):
        """드래그 진입 시 파일 타입 검증."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = Path(urls[0].toLocalFile())
                if file_path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS:
                    event.acceptProposedAction()
                    self._set_drag_hover_style(True)
                    return
        event.ignore()

    def dragLeaveEvent(self, event):
        """드래그 영역 벗어남."""
        self._set_drag_hover_style(False)

    def dropEvent(self, event: QDropEvent):
        """파일 드롭 처리."""
        self._set_drag_hover_style(False)
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = Path(urls[0].toLocalFile())
                if file_path.suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS:
                    event.acceptProposedAction()
                    self.file_dropped.emit(file_path)
                    return
        event.ignore()


class FrameGallery(QWidget):
    """추출된 프레임을 캐로셀/갤러리 형태로 표시하는 위젯."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.frame_paths: list[Path] = []
        self.frame_pixmaps: list[QPixmap] = []  # 메모리 캐시
        self.current_index = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # 메인 이미지 표시 영역
        self.image_label = QLabel()
        self.image_label.setMinimumSize(320, 180)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(
            "border: 1px solid #ccc; background: #2a2a2a; border-radius: 4px;"
        )
        self.image_label.setText("프레임이 추출되면 여기에 표시됩니다")
        self.image_label.setStyleSheet(
            "border: 1px solid #ccc; background: #2a2a2a; color: #888; border-radius: 4px;"
        )
        layout.addWidget(self.image_label, 1)

        # 네비게이션
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("◀ 이전")
        self.prev_btn.clicked.connect(self._prev_frame)
        self.prev_btn.setEnabled(False)
        nav_layout.addWidget(self.prev_btn)

        self.frame_info = QLabel("프레임 없음")
        self.frame_info.setAlignment(Qt.AlignCenter)
        nav_layout.addWidget(self.frame_info, 1)

        self.next_btn = QPushButton("다음 ▶")
        self.next_btn.clicked.connect(self._next_frame)
        self.next_btn.setEnabled(False)
        nav_layout.addWidget(self.next_btn)

        layout.addLayout(nav_layout)

        # 썸네일 스크롤 영역
        self.thumbnail_scroll = QScrollArea()
        self.thumbnail_scroll.setWidgetResizable(True)
        self.thumbnail_scroll.setFixedHeight(70)
        self.thumbnail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.thumbnail_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.thumbnail_widget = QWidget()
        self.thumbnail_layout = QHBoxLayout(self.thumbnail_widget)
        self.thumbnail_layout.setContentsMargins(2, 2, 2, 2)
        self.thumbnail_layout.setSpacing(4)
        self.thumbnail_scroll.setWidget(self.thumbnail_widget)
        layout.addWidget(self.thumbnail_scroll)

    def set_frames(self, frame_paths: list[Path]):
        """프레임 목록 설정."""
        self.frame_paths = frame_paths
        self.current_index = 0
        # 프레임을 메모리에 캐싱 (파일 삭제 후에도 표시 가능)
        self.frame_pixmaps = [QPixmap(str(p)) for p in frame_paths]
        self._update_thumbnails()
        self._update_display()
        self._update_nav_buttons()

    def clear(self):
        """갤러리 초기화."""
        self.frame_paths = []
        self.frame_pixmaps = []  # 메모리 캐시 정리
        self.current_index = 0
        self.image_label.clear()
        self.image_label.setText("프레임이 추출되면 여기에 표시됩니다")
        self.frame_info.setText("프레임 없음")
        self._clear_thumbnails()
        self._update_nav_buttons()

    def _update_display(self):
        if not self.frame_pixmaps:
            return
        # 현재 프레임 표시 (메모리 캐시에서 로드)
        pixmap = self.frame_pixmaps[self.current_index]
        if not pixmap.isNull():
            # 레이블 크기에 맞게 스케일
            scaled = pixmap.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.image_label.setPixmap(scaled)
        self.frame_info.setText(f"{self.current_index + 1} / {len(self.frame_pixmaps)}")

    def _update_thumbnails(self):
        self._clear_thumbnails()

        # 메모리 캐시에서 썸네일 생성 (파일 재로드 불필요)
        for i, pixmap in enumerate(self.frame_pixmaps):
            thumb_btn = QPushButton()
            if not pixmap.isNull():
                scaled = pixmap.scaled(60, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                thumb_btn.setIcon(QIcon(scaled))
                thumb_btn.setIconSize(QSize(60, 40))
            thumb_btn.setFixedSize(64, 44)
            thumb_btn.setStyleSheet(
                "QPushButton { border: 2px solid transparent; border-radius: 2px; }"
                "QPushButton:hover { border-color: #666; }"
            )
            thumb_btn.clicked.connect(lambda checked, idx=i: self._goto_frame(idx))
            self.thumbnail_layout.addWidget(thumb_btn)

        # 끝에 스트레치 추가
        self.thumbnail_layout.addStretch()

    def _clear_thumbnails(self):
        while self.thumbnail_layout.count():
            item = self.thumbnail_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _update_nav_buttons(self):
        has_frames = len(self.frame_pixmaps) > 0
        self.prev_btn.setEnabled(has_frames and self.current_index > 0)
        self.next_btn.setEnabled(has_frames and self.current_index < len(self.frame_pixmaps) - 1)

    def _prev_frame(self):
        if self.current_index > 0:
            self.current_index -= 1
            self._update_display()
            self._update_nav_buttons()

    def _next_frame(self):
        if self.current_index < len(self.frame_pixmaps) - 1:
            self.current_index += 1
            self._update_display()
            self._update_nav_buttons()

    def _goto_frame(self, idx: int):
        self.current_index = idx
        self._update_display()
        self._update_nav_buttons()

    def resizeEvent(self, event):
        """리사이즈 시 이미지 다시 스케일."""
        super().resizeEvent(event)
        if self.frame_pixmaps:
            self._update_display()
