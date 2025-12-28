"""분석 히스토리 목록 패널."""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class HistoryPanel(QGroupBox):
    """분석 히스토리 목록 패널."""

    item_clicked = Signal(object)  # QListWidgetItem
    refresh_clicked = Signal()
    delete_clicked = Signal()

    # 상태 상수
    STATE_LIST = 0
    STATE_EMPTY = 1
    STATE_ERROR = 2

    def __init__(self, parent=None):
        super().__init__("📚 분석 히스토리", parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 스택 위젯으로 상태별 화면 전환
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        self._setup_list_state()
        self._setup_empty_state()
        self._setup_error_state()
        self._setup_buttons(layout)

    def _setup_list_state(self):
        """히스토리 목록 상태 설정."""
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(0, 0, 0, 0)
        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self.item_clicked.emit)
        list_layout.addWidget(self.history_list)
        self.stack.addWidget(list_widget)

    def _setup_empty_state(self):
        """빈 상태 설정."""
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.setAlignment(Qt.AlignCenter)

        self.empty_icon = QLabel("📭")
        self.empty_icon.setStyleSheet("font-size: 48px;")
        self.empty_icon.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(self.empty_icon)

        self.empty_label = QLabel("저장된 분석 기록이 없습니다")
        self.empty_label.setStyleSheet("color: #666; font-size: 12px;")
        self.empty_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(self.empty_label)

        self.empty_hint = QLabel("영상을 분석한 후 저장하면\n여기에 기록이 표시됩니다")
        self.empty_hint.setStyleSheet("color: #999; font-size: 11px;")
        self.empty_hint.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(self.empty_hint)

        self.stack.addWidget(empty_widget)

    def _setup_error_state(self):
        """오류 상태 설정."""
        error_widget = QWidget()
        error_layout = QVBoxLayout(error_widget)
        error_layout.setAlignment(Qt.AlignCenter)

        self.error_icon = QLabel("⚠️")
        self.error_icon.setStyleSheet("font-size: 48px;")
        self.error_icon.setAlignment(Qt.AlignCenter)
        error_layout.addWidget(self.error_icon)

        self.error_label = QLabel("히스토리를 불러올 수 없습니다")
        self.error_label.setStyleSheet("color: #c0392b; font-size: 12px; font-weight: bold;")
        self.error_label.setAlignment(Qt.AlignCenter)
        error_layout.addWidget(self.error_label)

        self.error_detail = QLabel("")
        self.error_detail.setStyleSheet("color: #666; font-size: 10px;")
        self.error_detail.setAlignment(Qt.AlignCenter)
        self.error_detail.setWordWrap(True)
        error_layout.addWidget(self.error_detail)

        self.retry_btn = QPushButton("🔄 다시 시도")
        self.retry_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.retry_btn.clicked.connect(self.refresh_clicked.emit)
        error_layout.addWidget(self.retry_btn, alignment=Qt.AlignCenter)

        self.stack.addWidget(error_widget)

    def _setup_buttons(self, layout):
        """버튼 레이아웃 설정."""
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

    def show_list(self):
        """히스토리 목록 상태 표시."""
        self.stack.setCurrentIndex(self.STATE_LIST)
        self.delete_btn.setEnabled(True)

    def show_empty(self):
        """빈 상태 표시."""
        self.stack.setCurrentIndex(self.STATE_EMPTY)
        self.delete_btn.setEnabled(False)

    def show_error(self, error_message: str = ""):
        """오류 상태 표시."""
        if error_message:
            self.error_detail.setText(error_message)
        else:
            self.error_detail.setText("파일 시스템 접근 오류가 발생했습니다")
        self.stack.setCurrentIndex(self.STATE_ERROR)
        self.delete_btn.setEnabled(False)

    def get_selected_item(self) -> Optional[QListWidgetItem]:
        """선택된 항목 반환."""
        return self.history_list.currentItem()

    def get_selected_record_id(self) -> Optional[str]:
        """선택된 항목의 record_id 반환."""
        item = self.history_list.currentItem()
        if item:
            return item.data(Qt.UserRole)
        return None
