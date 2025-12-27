"""FFmpeg를 사용한 I-Frame 추출 모듈."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class VideoInfo:
    """영상 메타데이터."""

    path: Path
    duration: float  # 초
    width: int
    height: int
    fps: float
    codec: str
    size_bytes: int

    @property
    def resolution(self) -> tuple[int, int]:
        return (self.width, self.height)

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)

    @property
    def duration_str(self) -> str:
        """사람이 읽기 쉬운 시간 형식으로 변환."""
        minutes, seconds = divmod(int(self.duration), 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}시간 {minutes}분 {seconds}초"
        elif minutes > 0:
            return f"{minutes}분 {seconds}초"
        else:
            return f"{seconds}초"


class FrameExtractor:
    """FFmpeg를 사용하여 영상에서 프레임을 추출하는 클래스."""

    def __init__(
        self,
        ffmpeg_path: Optional[str] = None,
        ffprobe_path: Optional[str] = None,
    ):
        """
        Args:
            ffmpeg_path: FFmpeg 실행 파일 경로. None이면 시스템 PATH에서 검색.
            ffprobe_path: FFprobe 실행 파일 경로. None이면 시스템 PATH에서 검색.
        """
        self.ffmpeg = ffmpeg_path or shutil.which("ffmpeg")
        self.ffprobe = ffprobe_path or shutil.which("ffprobe")

        if not self.ffmpeg:
            raise RuntimeError("FFmpeg를 찾을 수 없습니다. FFmpeg를 설치해주세요.")
        if not self.ffprobe:
            raise RuntimeError("FFprobe를 찾을 수 없습니다. FFmpeg를 설치해주세요.")

    def get_video_info(self, video_path: Path) -> VideoInfo:
        """
        영상 메타데이터를 추출합니다.

        Args:
            video_path: 영상 파일 경로

        Returns:
            VideoInfo: 영상 메타데이터

        Raises:
            FileNotFoundError: 파일이 존재하지 않을 때
            ValueError: 유효하지 않은 영상 파일일 때
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {video_path}")

        cmd = [
            self.ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(video_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise ValueError(f"영상 정보를 읽을 수 없습니다: {result.stderr}")

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            raise ValueError(f"FFprobe 출력을 파싱할 수 없습니다: {e}") from e

        # 비디오 스트림 찾기
        video_stream = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                video_stream = stream
                break

        if not video_stream:
            raise ValueError("영상 스트림을 찾을 수 없습니다.")

        format_info = data.get("format", {})

        # FPS 파싱 (예: "30000/1001" -> 29.97)
        fps_str = video_stream.get("r_frame_rate", "0/1")
        try:
            num, den = map(int, fps_str.split("/"))
            fps = num / den if den != 0 else 0.0
        except (ValueError, ZeroDivisionError):
            fps = 0.0

        return VideoInfo(
            path=video_path,
            duration=float(format_info.get("duration", 0)),
            width=int(video_stream.get("width", 0)),
            height=int(video_stream.get("height", 0)),
            fps=fps,
            codec=video_stream.get("codec_name", "unknown"),
            size_bytes=int(format_info.get("size", 0)),
        )

    def extract_frames(
        self,
        video_path: Path,
        output_dir: Path,
        interval: Optional[float] = None,
        max_dimension: int = 1280,
        quality: int = 2,
    ) -> list[Path]:
        """
        영상에서 프레임을 추출합니다.

        Args:
            video_path: 영상 파일 경로
            output_dir: 프레임을 저장할 디렉토리
            interval: 추출 간격 (초). None이면 모든 I-Frame 추출.
            max_dimension: 이미지 최대 크기 (가로 기준)
            quality: JPEG 품질 (1-31, 낮을수록 고품질)

        Returns:
            list[Path]: 추출된 프레임 파일 경로 목록

        Raises:
            FileNotFoundError: 영상 파일이 존재하지 않을 때
            RuntimeError: FFmpeg 실행 실패 시
        """
        video_path = Path(video_path)
        output_dir = Path(output_dir)

        if not video_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {video_path}")

        output_dir.mkdir(parents=True, exist_ok=True)
        output_pattern = output_dir / "frame_%04d.jpg"

        # 스케일 필터: 가로가 max_dimension을 초과하면 비율 유지하며 축소
        scale_filter = f"scale='min({max_dimension},iw):-2'"

        if interval is not None and interval > 0:
            # 간격 기반 추출
            vf_filter = f"fps=1/{interval},{scale_filter}"
        else:
            # 모든 I-Frame 추출
            vf_filter = f"select='eq(pict_type,I)',{scale_filter}"

        cmd = [
            self.ffmpeg,
            "-i", str(video_path),
            "-vf", vf_filter,
            "-vsync", "vfr",
            "-q:v", str(quality),
            "-y",  # 기존 파일 덮어쓰기
            str(output_pattern),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            # FFmpeg가 에러를 출력해도 정상 종료하는 경우가 있으므로
            # 파일이 생성되었는지 확인
            frames = sorted(output_dir.glob("frame_*.jpg"))
            if not frames:
                raise RuntimeError(f"프레임 추출 실패: {result.stderr}")

        frames = sorted(output_dir.glob("frame_*.jpg"))
        return frames

    def extract_frames_with_timestamps(
        self,
        video_path: Path,
        output_dir: Path,
        interval: Optional[float] = None,
        max_dimension: int = 1280,
    ) -> list[tuple[Path, float]]:
        """
        프레임을 추출하고 각 프레임의 타임스탬프를 반환합니다.

        Args:
            video_path: 영상 파일 경로
            output_dir: 프레임을 저장할 디렉토리
            interval: 추출 간격 (초). None이면 모든 I-Frame 추출.
            max_dimension: 이미지 최대 크기

        Returns:
            list[tuple[Path, float]]: (프레임 경로, 타임스탬프) 튜플 목록
        """
        frames = self.extract_frames(
            video_path, output_dir, interval, max_dimension
        )

        if interval is not None and interval > 0:
            # 간격 기반 추출: 간격으로 타임스탬프 계산
            return [(frame, i * interval) for i, frame in enumerate(frames)]
        else:
            # I-Frame 추출: 평균 간격 추정 (정확하지 않음)
            video_info = self.get_video_info(video_path)
            estimated_interval = video_info.duration / len(frames) if frames else 0
            return [
                (frame, i * estimated_interval)
                for i, frame in enumerate(frames)
            ]

    def count_iframes(self, video_path: Path) -> int:
        """
        영상의 I-Frame 개수를 카운트합니다.

        Args:
            video_path: 영상 파일 경로

        Returns:
            int: I-Frame 개수

        Note:
            이 작업은 전체 영상을 스캔해야 하므로 시간이 걸릴 수 있습니다.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {video_path}")

        cmd = [
            self.ffprobe,
            "-v", "quiet",
            "-select_streams", "v:0",
            "-count_packets",
            "-show_entries", "stream=nb_read_packets",
            "-of", "csv=p=0",
            "-skip_frame", "nokey",  # I-Frame만 카운트
            str(video_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            # 폴백: 영상 길이로 추정
            video_info = self.get_video_info(video_path)
            return int(video_info.duration / 3)  # 평균 3초당 1개로 추정

        try:
            return int(result.stdout.strip())
        except ValueError:
            # 파싱 실패 시 추정
            video_info = self.get_video_info(video_path)
            return int(video_info.duration / 3)
