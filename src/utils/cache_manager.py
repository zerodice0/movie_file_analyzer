"""임시 파일(캐시) 관리 모듈."""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


@dataclass
class CacheInfo:
    """캐시 정보."""

    video_hash: str
    video_name: str
    cache_path: Path
    frame_count: int
    size_bytes: int
    created_at: datetime

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)

    @property
    def age_days(self) -> float:
        return (datetime.now() - self.created_at).total_seconds() / 86400


class CacheManager:
    """추출된 프레임 캐시를 관리합니다."""

    DEFAULT_CACHE_DIR = Path.home() / ".movie_file_analyzer" / "cache"
    DEFAULT_MAX_SIZE_MB = 1024  # 1GB
    DEFAULT_MAX_AGE_DAYS = 7

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        auto_cleanup: bool = True,
        max_size_mb: float = DEFAULT_MAX_SIZE_MB,
        max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    ):
        """
        Args:
            cache_dir: 캐시 디렉토리 경로
            auto_cleanup: 분석 완료 후 자동 삭제 여부
            max_size_mb: 최대 캐시 크기 (MB)
            max_age_days: 캐시 최대 수명 (일)
        """
        self.cache_dir = cache_dir or self.DEFAULT_CACHE_DIR
        self.auto_cleanup = auto_cleanup
        self.max_size_mb = max_size_mb
        self.max_age_days = max_age_days

        # 캐시 디렉토리 생성
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _compute_hash(self, video_path: Path) -> str:
        """영상 파일의 해시를 계산합니다."""
        # 파일 전체 해시는 시간이 오래 걸리므로
        # 파일명 + 크기 + 수정 시간으로 해시 생성
        video_path = Path(video_path)
        stat = video_path.stat()
        key = f"{video_path.name}_{stat.st_size}_{stat.st_mtime}"
        return hashlib.md5(key.encode()).hexdigest()[:12]

    def get_cache_path(self, video_path: Path) -> Path:
        """영상에 대한 캐시 디렉토리 경로를 반환합니다."""
        video_hash = self._compute_hash(video_path)
        return self.cache_dir / video_hash

    def get_frames_dir(self, video_path: Path) -> Path:
        """영상의 프레임 저장 디렉토리를 반환합니다."""
        return self.get_cache_path(video_path) / "frames"

    def create_cache_dir(self, video_path: Path) -> Path:
        """캐시 디렉토리를 생성하고 경로를 반환합니다."""
        frames_dir = self.get_frames_dir(video_path)
        frames_dir.mkdir(parents=True, exist_ok=True)
        return frames_dir

    def has_cache(self, video_path: Path) -> bool:
        """영상에 대한 캐시가 존재하는지 확인합니다."""
        frames_dir = self.get_frames_dir(video_path)
        if not frames_dir.exists():
            return False
        return any(frames_dir.glob("frame_*.jpg"))

    def get_cached_frames(self, video_path: Path) -> list[Path]:
        """캐시된 프레임 목록을 반환합니다."""
        frames_dir = self.get_frames_dir(video_path)
        if not frames_dir.exists():
            return []
        return sorted(frames_dir.glob("frame_*.jpg"))

    def cleanup_video_cache(self, video_path: Path) -> bool:
        """특정 영상의 캐시를 삭제합니다."""
        cache_path = self.get_cache_path(video_path)
        if cache_path.exists():
            shutil.rmtree(cache_path, ignore_errors=True)
            return True
        return False

    def cleanup_by_hash(self, video_hash: str) -> bool:
        """해시로 캐시를 삭제합니다."""
        cache_path = self.cache_dir / video_hash
        if cache_path.exists():
            shutil.rmtree(cache_path, ignore_errors=True)
            return True
        return False

    def cleanup_all(self) -> int:
        """모든 캐시를 삭제합니다."""
        count = 0
        if self.cache_dir.exists():
            for item in self.cache_dir.iterdir():
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                    count += 1
        return count

    def cleanup_old_cache(self, max_age_days: Optional[int] = None) -> int:
        """오래된 캐시를 삭제합니다."""
        max_age = max_age_days or self.max_age_days
        cutoff = datetime.now() - timedelta(days=max_age)
        count = 0

        if not self.cache_dir.exists():
            return 0

        for cache_dir in self.cache_dir.iterdir():
            if cache_dir.is_dir():
                try:
                    mtime = datetime.fromtimestamp(cache_dir.stat().st_mtime)
                    if mtime < cutoff:
                        shutil.rmtree(cache_dir, ignore_errors=True)
                        count += 1
                except OSError:
                    continue

        return count

    def cleanup_if_size_exceeded(self) -> int:
        """캐시 크기가 제한을 초과하면 오래된 것부터 삭제합니다."""
        current_size = self.get_total_size()
        max_size_bytes = self.max_size_mb * 1024 * 1024

        if current_size <= max_size_bytes:
            return 0

        # 수정 시간 순으로 정렬 (오래된 것 먼저)
        caches = []
        for cache_dir in self.cache_dir.iterdir():
            if cache_dir.is_dir():
                try:
                    caches.append((cache_dir, cache_dir.stat().st_mtime))
                except OSError:
                    continue

        caches.sort(key=lambda x: x[1])  # 오래된 것 먼저

        count = 0
        for cache_dir, _ in caches:
            if current_size <= max_size_bytes:
                break

            try:
                size = sum(
                    f.stat().st_size for f in cache_dir.rglob("*") if f.is_file()
                )
                shutil.rmtree(cache_dir, ignore_errors=True)
                current_size -= size
                count += 1
            except OSError:
                continue

        return count

    def get_total_size(self) -> int:
        """전체 캐시 크기를 반환합니다 (바이트)."""
        if not self.cache_dir.exists():
            return 0

        total = 0
        for f in self.cache_dir.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except OSError:
                    continue
        return total

    def get_total_size_mb(self) -> float:
        """전체 캐시 크기를 반환합니다 (MB)."""
        return self.get_total_size() / (1024 * 1024)

    def get_cache_count(self) -> int:
        """캐시된 영상 수를 반환합니다."""
        if not self.cache_dir.exists():
            return 0
        return sum(1 for d in self.cache_dir.iterdir() if d.is_dir())

    def list_caches(self) -> list[CacheInfo]:
        """모든 캐시 정보를 반환합니다."""
        caches = []

        if not self.cache_dir.exists():
            return caches

        for cache_dir in self.cache_dir.iterdir():
            if not cache_dir.is_dir():
                continue

            frames_dir = cache_dir / "frames"
            frames = list(frames_dir.glob("frame_*.jpg")) if frames_dir.exists() else []

            try:
                size = sum(
                    f.stat().st_size for f in cache_dir.rglob("*") if f.is_file()
                )
                created_at = datetime.fromtimestamp(cache_dir.stat().st_mtime)
            except OSError:
                continue

            caches.append(
                CacheInfo(
                    video_hash=cache_dir.name,
                    video_name=cache_dir.name,  # 실제 이름은 알 수 없음
                    cache_path=cache_dir,
                    frame_count=len(frames),
                    size_bytes=size,
                    created_at=created_at,
                )
            )

        return caches

    def auto_cleanup_after_analysis(self, video_path: Path) -> bool:
        """
        분석 완료 후 자동 정리를 수행합니다.

        auto_cleanup이 True인 경우에만 캐시를 삭제합니다.
        """
        if self.auto_cleanup:
            return self.cleanup_video_cache(video_path)
        return False

    def format_size(self, size_bytes: int) -> str:
        """크기를 사람이 읽기 쉬운 형식으로 변환합니다."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
