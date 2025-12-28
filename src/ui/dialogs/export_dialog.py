"""내보내기 다이얼로그."""

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class ExportDialog(QDialog):
    """내보내기 옵션 선택 다이얼로그."""

    def __init__(self, video_path: Path, has_sidecar: bool, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.has_sidecar = has_sidecar
        self.export_path: Path | None = None

        self.setWindowTitle("내보내기")
        self.setMinimumWidth(450)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 설명 레이블
        info_label = QLabel(f"📹 {self.video_path.name}")
        info_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(info_label)

        # 체크박스 영역
        checkbox_label = QLabel("내보낼 파일 선택:")
        layout.addWidget(checkbox_label)

        self.video_check = QCheckBox("영상 파일")
        self.video_check.setChecked(True)
        layout.addWidget(self.video_check)

        self.sidecar_check = QCheckBox("사이드카 (.analysis.json)")
        self.sidecar_check.setChecked(self.has_sidecar)
        self.sidecar_check.setEnabled(self.has_sidecar)
        if not self.has_sidecar:
            self.sidecar_check.setToolTip("사이드카 파일이 존재하지 않습니다")
        layout.addWidget(self.sidecar_check)

        # 경로 선택
        path_label = QLabel("저장 위치:")
        layout.addWidget(path_label)

        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("폴더를 선택하세요")
        browse_btn = QPushButton("📂 찾아보기...")
        browse_btn.clicked.connect(self._on_browse)
        path_layout.addWidget(self.path_edit, 1)
        path_layout.addWidget(browse_btn)
        layout.addLayout(path_layout)

        layout.addStretch()

        # 버튼
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        self.ok_button = button_box.button(QDialogButtonBox.Ok)
        self.ok_button.setText("📦 내보내기")
        self.ok_button.setEnabled(False)
        layout.addWidget(button_box)

    def _on_browse(self):
        folder = QFileDialog.getExistingDirectory(self, "저장할 폴더 선택")
        if folder:
            self.export_path = Path(folder)
            self.path_edit.setText(folder)
            self._update_ok_button()

    def _update_ok_button(self):
        """OK 버튼 활성화 상태 업데이트."""
        has_selection = self.video_check.isChecked() or self.sidecar_check.isChecked()
        has_path = self.export_path is not None
        self.ok_button.setEnabled(has_selection and has_path)

    def _on_accept(self):
        if self.export_path:
            self.accept()

    def get_options(self) -> dict:
        """선택된 옵션 반환."""
        return {
            "video": self.video_check.isChecked(),
            "sidecar": self.sidecar_check.isChecked(),
            "path": self.export_path,
        }
