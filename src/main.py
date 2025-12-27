"""Movie File Analyzer - 메인 엔트리포인트."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .ui.main_window import MainWindow


def main():
    """애플리케이션 메인 함수."""
    app = QApplication(sys.argv)

    # 앱 스타일 설정
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    # Qt 이벤트 루프 실행
    return_code = app.exec()
    sys.exit(return_code)


if __name__ == "__main__":
    main()
