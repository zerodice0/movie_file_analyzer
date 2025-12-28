"""설정 패널."""

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from ...data.models import AppConfig


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
