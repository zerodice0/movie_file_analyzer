"""YouTube 다운로드 관련 핸들러."""

from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from ...core.youtube_downloader import YouTubeDownloader


class YouTubeHandlerMixin:
    """YouTube 다운로드 관련 핸들러 믹스인."""

    def _on_youtube_download_clicked(self, url: str):
        """YouTube 다운로드 버튼 클릭."""
        if not YouTubeDownloader.is_youtube_url(url):
            QMessageBox.warning(
                self, "잘못된 URL",
                "유효한 YouTube URL이 아닙니다.\n"
                "예: https://youtube.com/watch?v=... 또는 https://youtu.be/...",
            )
            return

        if not YouTubeDownloader.is_available():
            QMessageBox.warning(
                self, "yt-dlp 미설치",
                "yt-dlp가 설치되어 있지 않습니다.\n\n"
                "설치 방법:\n"
                "  • run.sh에서 📦 의존성 관리 메뉴 이용\n"
                "  • pip install --user yt-dlp\n"
                "  • brew install yt-dlp",
            )
            return

        if self.download_worker and self.download_worker.isRunning():
            QMessageBox.warning(self, "알림", "다운로드가 이미 진행 중입니다.")
            return

        self._start_youtube_download(url)

    def _start_youtube_download(self, url: str):
        """YouTube 다운로드 시작."""
        from ..download_worker import DownloadWorker

        # UI 비활성화
        self.file_panel.set_youtube_enabled(False)
        self.file_panel.set_browse_enabled(False)
        self.settings_panel.set_analyze_enabled(False)
        self.progress_panel.reset()
        self.progress_panel.set_progress(0, "📥 YouTube 다운로드 준비 중...")

        # 다운로드 시작
        self.download_worker = DownloadWorker(url)
        self.download_worker.progress.connect(self._on_download_progress)
        self.download_worker.finished.connect(self._on_download_finished)
        self.download_worker.error.connect(self._on_download_error)
        self.download_worker.start()

    def _on_download_progress(self, percent: float, message: str):
        """다운로드 진행률 업데이트."""
        self.progress_panel.set_progress(int(percent * 0.9), message)

    def _on_download_finished(self, success: bool, file_path: Path, title: str):
        """다운로드 완료."""
        self.file_panel.set_youtube_enabled(True)
        self.file_panel.set_browse_enabled(True)

        if success and file_path and file_path.exists():
            self.progress_panel.set_progress(95, f"✅ 다운로드 완료: {title}")
            self.file_panel.clear_youtube_url()
            self._load_video(file_path)
        else:
            self.progress_panel.set_progress(0, "❌ 다운로드 실패")

    def _on_download_error(self, error_message: str):
        """다운로드 에러."""
        self.file_panel.set_youtube_enabled(True)
        self.file_panel.set_browse_enabled(True)
        self.progress_panel.set_progress(0, "❌ 다운로드 오류")
        QMessageBox.critical(self, "다운로드 오류", error_message)
