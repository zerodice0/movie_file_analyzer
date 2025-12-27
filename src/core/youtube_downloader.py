"""YouTube 영상 다운로드 모듈 (yt-dlp 래퍼)."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional


@dataclass
class DownloadProgress:
    """다운로드 진행 상태."""

    percent: float
    downloaded_bytes: int
    total_bytes: int
    speed: str
    eta: str


@dataclass
class DownloadResult:
    """다운로드 결과."""

    success: bool
    file_path: Optional[Path]
    title: str
    error_message: Optional[str] = None


class YouTubeDownloader:
    """yt-dlp를 사용한 YouTube 다운로드 래퍼."""

    # YouTube URL 패턴
    YOUTUBE_PATTERNS = [
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+",
        r"(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+",
        r"(?:https?://)?youtu\.be/[\w-]+",
        r"(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+",
    ]

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Args:
            output_dir: 다운로드 디렉토리 (기본: ~/.movie_file_analyzer/downloads)
        """
        if output_dir is None:
            output_dir = Path.home() / ".movie_file_analyzer" / "downloads"
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def is_available() -> bool:
        """yt-dlp가 설치되어 있는지 확인."""
        return shutil.which("yt-dlp") is not None or shutil.which("yt_dlp") is not None

    @staticmethod
    def get_command() -> str:
        """yt-dlp 명령어 반환."""
        if shutil.which("yt-dlp"):
            return "yt-dlp"
        elif shutil.which("yt_dlp"):
            return "yt_dlp"
        raise RuntimeError("yt-dlp가 설치되어 있지 않습니다.")

    @classmethod
    def is_youtube_url(cls, url: str) -> bool:
        """YouTube URL인지 확인."""
        for pattern in cls.YOUTUBE_PATTERNS:
            if re.match(pattern, url.strip()):
                return True
        return False

    def get_video_info(self, url: str) -> dict:
        """영상 정보 조회 (제목, 길이 등)."""
        cmd = self.get_command()
        result = subprocess.run(
            [
                cmd,
                "--dump-json",
                "--no-download",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            raise RuntimeError(f"영상 정보 조회 실패: {result.stderr}")

        import json

        return json.loads(result.stdout)

    def download(
        self,
        url: str,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
        format_option: str = "best[ext=mp4]/best",
    ) -> DownloadResult:
        """
        YouTube 영상 다운로드.

        Args:
            url: YouTube URL
            progress_callback: 진행률 콜백 함수
            format_option: yt-dlp 포맷 옵션

        Returns:
            DownloadResult: 다운로드 결과
        """
        if not self.is_available():
            return DownloadResult(
                success=False,
                file_path=None,
                title="",
                error_message="yt-dlp가 설치되어 있지 않습니다.",
            )

        try:
            # 영상 정보 먼저 조회
            info = self.get_video_info(url)
            title = info.get("title", "unknown")
            video_id = info.get("id", "unknown")

            # 안전한 파일명 생성
            safe_title = re.sub(r'[<>:"/\\|?*]', "_", title)[:50]
            output_template = str(self.output_dir / f"{safe_title}_{video_id}.%(ext)s")

            cmd = self.get_command()
            args = [
                cmd,
                "-f",
                format_option,
                "-o",
                output_template,
                "--newline",  # 진행률 파싱을 위해
                url,
            ]

            process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            final_path = None

            # 출력 스트리밍 및 진행률 파싱
            for line in process.stdout:
                line = line.strip()

                # 진행률 파싱: [download]  50.0% of 100.00MiB at  5.00MiB/s ETA 00:10
                if "[download]" in line and "%" in line:
                    match = re.search(
                        r"(\d+\.?\d*)%\s+of\s+~?(\d+\.?\d*)([\w]+)\s+at\s+([\d.]+\w+/s)\s+ETA\s+([\d:]+)",
                        line,
                    )
                    if match and progress_callback:
                        percent = float(match.group(1))
                        progress = DownloadProgress(
                            percent=percent,
                            downloaded_bytes=0,  # 간단화
                            total_bytes=0,
                            speed=match.group(4),
                            eta=match.group(5),
                        )
                        progress_callback(progress)

                # 다운로드 완료 시 파일 경로 캡처
                # [download] Destination: /path/to/file.mp4
                if "[download] Destination:" in line:
                    final_path = Path(line.split("Destination:")[1].strip())

                # 이미 다운로드된 경우
                # [download] /path/to/file.mp4 has already been downloaded
                if "has already been downloaded" in line:
                    path_match = re.search(r"\[download\]\s+(.+?)\s+has already", line)
                    if path_match:
                        final_path = Path(path_match.group(1))

            process.wait()

            if process.returncode != 0:
                return DownloadResult(
                    success=False,
                    file_path=None,
                    title=title,
                    error_message="다운로드 실패",
                )

            # 다운로드된 파일 찾기 (final_path가 없는 경우)
            if final_path is None:
                for ext in ["mp4", "webm", "mkv"]:
                    candidate = self.output_dir / f"{safe_title}_{video_id}.{ext}"
                    if candidate.exists():
                        final_path = candidate
                        break

            return DownloadResult(
                success=True,
                file_path=final_path,
                title=title,
            )

        except subprocess.TimeoutExpired:
            return DownloadResult(
                success=False,
                file_path=None,
                title="",
                error_message="다운로드 시간 초과",
            )
        except Exception as e:
            return DownloadResult(
                success=False,
                file_path=None,
                title="",
                error_message=str(e),
            )
