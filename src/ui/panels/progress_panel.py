"""진행 상황 표시 패널."""

from PySide6.QtWidgets import (
    QGroupBox,
    QLabel,
    QProgressBar,
    QVBoxLayout,
)


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
