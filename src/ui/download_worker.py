"""YouTube 다운로드 백그라운드 스레드."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from ..core.youtube_downloader import DownloadProgress, YouTubeDownloader


class DownloadWorker(QThread):
    """YouTube 다운로드 백그라운드 스레드."""

    progress = Signal(float, str)  # 진행률(%), 메시지
    finished = Signal(bool, object, str)  # 성공 여부, Path, 제목
    error = Signal(str)  # 에러 메시지

    def __init__(self, url: str, output_dir: Path = None):
        super().__init__()
        self.url = url
        self.downloader = YouTubeDownloader(output_dir)
        self._cancelled = False

    def cancel(self):
        """다운로드 취소."""
        self._cancelled = True

    def _on_progress(self, progress: DownloadProgress):
        """진행률 업데이트 콜백."""
        if self._cancelled:
            return

        message = f"다운로드 중... {progress.percent:.1f}%"
        if progress.speed:
            message += f" ({progress.speed})"
        if progress.eta:
            message += f" ETA: {progress.eta}"

        self.progress.emit(progress.percent, message)

    def run(self):
        """다운로드 실행."""
        try:
            if not YouTubeDownloader.is_available():
                self.error.emit("yt-dlp가 설치되어 있지 않습니다.\n📦 의존성 관리에서 설치해주세요.")
                return

            self.progress.emit(0, "영상 정보 조회 중...")

            result = self.downloader.download(
                url=self.url,
                progress_callback=self._on_progress,
            )

            if self._cancelled:
                self.error.emit("다운로드가 취소되었습니다.")
                return

            if result.success:
                self.progress.emit(100, "다운로드 완료!")
                self.finished.emit(True, result.file_path, result.title)
            else:
                self.error.emit(result.error_message or "다운로드 실패")

        except Exception as e:
            self.error.emit(str(e))
