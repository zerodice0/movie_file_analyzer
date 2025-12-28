"""CLI 유틸리티 함수들."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Optional


def check_dependencies() -> dict[str, bool]:
    """의존성 설치 상태를 확인합니다."""
    return {
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "ffprobe": shutil.which("ffprobe") is not None,
        "gemini": shutil.which("gemini") is not None,
        "yt-dlp": shutil.which("yt-dlp") is not None or shutil.which("yt_dlp") is not None,
    }


def is_youtube_url(url: str) -> bool:
    """YouTube URL인지 확인합니다."""
    youtube_patterns = [
        r'(https?://)?(www\.)?youtube\.com/watch\?v=',
        r'(https?://)?(www\.)?youtu\.be/',
        r'(https?://)?(www\.)?youtube\.com/shorts/',
    ]
    return any(re.match(pattern, url) for pattern in youtube_patterns)


def download_youtube(url: str, output_dir: Optional[Path] = None) -> tuple[bool, str, Optional[Path]]:
    """YouTube 영상을 다운로드합니다."""
    try:
        from ..core.youtube_downloader import YouTubeDownloader

        downloader = YouTubeDownloader()
        if not downloader.is_available():
            return False, "yt-dlp가 설치되어 있지 않습니다.", None

        if output_dir is None:
            output_dir = Path.home() / ".movie_file_analyzer" / "downloads"
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"🔄 YouTube 영상 다운로드 중: {url}")

        def progress_callback(progress):
            if progress.percent:
                print(f"   진행률: {progress.percent:.1f}%", end="\r")

        result = downloader.download(url, output_dir, progress_callback=progress_callback)
        print()

        if result.success:
            return True, f"다운로드 완료: {result.file_path}", result.file_path
        else:
            return False, f"다운로드 실패: {result.error_message}", None

    except ImportError:
        return False, "YouTube 다운로더 모듈을 로드할 수 없습니다.", None
    except Exception as e:
        return False, f"다운로드 오류: {e}", None
