"""다운로드 및 캐시 저장소 관리 모듈."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class StorageInfo:
    """저장소 정보."""

    path: Path
    total_size: int  # bytes
    file_count: int
    exists: bool

    @property
    def size_mb(self) -> float:
        return self.total_size / (1024 * 1024)

    @property
    def size_formatted(self) -> str:
        return StorageManager.format_size(self.total_size)


class StorageManager:
    """다운로드 폴더 및 저장소 관리."""

    DEFAULT_DOWNLOAD_DIR = Path.home() / ".movie_file_analyzer" / "downloads"
    DEFAULT_CACHE_DIR = Path.home() / ".movie_file_analyzer" / "cache"

    def __init__(
        self,
        download_dir: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
    ):
        """
        Args:
            download_dir: 다운로드 디렉토리 경로
            cache_dir: 캐시 디렉토리 경로
        """
        self.download_dir = download_dir or self.DEFAULT_DOWNLOAD_DIR
        self.cache_dir = cache_dir or self.DEFAULT_CACHE_DIR

    def get_download_info(self) -> StorageInfo:
        """다운로드 폴더 정보를 반환합니다."""
        return self._get_dir_info(self.download_dir)

    def get_cache_info(self) -> StorageInfo:
        """캐시 폴더 정보를 반환합니다."""
        return self._get_dir_info(self.cache_dir)

    def _get_dir_info(self, path: Path) -> StorageInfo:
        """디렉토리 정보를 반환합니다."""
        if not path.exists():
            return StorageInfo(
                path=path,
                total_size=0,
                file_count=0,
                exists=False,
            )

        total_size = 0
        file_count = 0

        for f in path.rglob("*"):
            if f.is_file():
                try:
                    total_size += f.stat().st_size
                    file_count += 1
                except OSError:
                    continue

        return StorageInfo(
            path=path,
            total_size=total_size,
            file_count=file_count,
            exists=True,
        )

    def get_download_files(self) -> list[Path]:
        """다운로드된 파일 목록을 반환합니다."""
        if not self.download_dir.exists():
            return []

        video_extensions = {".mp4", ".mkv", ".webm", ".avi", ".mov"}
        files = []

        for f in self.download_dir.iterdir():
            if f.is_file() and f.suffix.lower() in video_extensions:
                files.append(f)

        return sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)

    def cleanup_downloads(self) -> int:
        """다운로드 폴더를 정리합니다."""
        if not self.download_dir.exists():
            return 0

        count = 0
        for f in self.download_dir.iterdir():
            if f.is_file():
                try:
                    f.unlink()
                    count += 1
                except OSError:
                    continue

        return count

    def open_folder(self, path: Path) -> bool:
        """파일 탐색기에서 폴더를 엽니다."""
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)

        try:
            if sys.platform == "darwin":  # macOS
                subprocess.run(["open", str(path)], check=True)
            elif sys.platform == "win32":  # Windows
                subprocess.run(["explorer", str(path)], check=True)
            else:  # Linux
                subprocess.run(["xdg-open", str(path)], check=True)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def open_download_folder(self) -> bool:
        """다운로드 폴더를 엽니다."""
        return self.open_folder(self.download_dir)

    def open_cache_folder(self) -> bool:
        """캐시 폴더를 엽니다."""
        return self.open_folder(self.cache_dir)

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """크기를 사람이 읽기 쉬운 형식으로 변환합니다."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    @staticmethod
    def shorten_path(path: Path, max_length: int = 40) -> str:
        """경로를 축약하여 반환합니다."""
        path_str = str(path)

        # ~ 표기로 홈 디렉토리 축약
        home = str(Path.home())
        if path_str.startswith(home):
            path_str = "~" + path_str[len(home):]

        if len(path_str) <= max_length:
            return path_str

        # 너무 긴 경우 중간 생략
        parts = Path(path_str).parts
        if len(parts) <= 3:
            return path_str

        return f"{parts[0]}/.../{parts[-1]}"
