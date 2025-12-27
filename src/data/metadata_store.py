"""메타데이터 저장소 - JSON 사이드카 및 영상 파일 내부 메타데이터 관리."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import AnalysisRecord


class MetadataStore:
    """분석 결과 메타데이터를 저장하고 관리합니다."""

    SIDECAR_SUFFIX = ".analysis.json"
    CENTRAL_STORE_FILE = "analysis_history.json"

    def __init__(self, base_dir: Optional[Path] = None):
        """
        Args:
            base_dir: 중앙 저장소 디렉토리 (기본: ~/.movie_file_analyzer)
        """
        self.base_dir = base_dir or (Path.home() / ".movie_file_analyzer")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.central_store_path = self.base_dir / self.CENTRAL_STORE_FILE

    # =========================================================================
    # JSON 사이드카 파일 관리
    # =========================================================================

    def get_sidecar_path(self, video_path: Path) -> Path:
        """영상 파일의 사이드카 JSON 경로를 반환합니다."""
        return Path(str(video_path) + self.SIDECAR_SUFFIX)

    def save_sidecar(self, record: AnalysisRecord) -> Path:
        """
        분석 결과를 영상 파일 옆에 JSON 사이드카로 저장합니다.

        Args:
            record: 분석 기록

        Returns:
            Path: 저장된 사이드카 파일 경로
        """
        video_path = Path(record.video_path)
        sidecar_path = self.get_sidecar_path(video_path)

        data = asdict(record)
        data["_metadata"] = {
            "version": "1.0",
            "created_at": record.created_at,
            "updated_at": datetime.now().isoformat(),
        }

        with open(sidecar_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return sidecar_path

    def load_sidecar(self, video_path: Path) -> Optional[AnalysisRecord]:
        """
        영상 파일의 사이드카 JSON을 로드합니다.

        Args:
            video_path: 영상 파일 경로

        Returns:
            Optional[AnalysisRecord]: 분석 기록 또는 None
        """
        sidecar_path = self.get_sidecar_path(video_path)

        if not sidecar_path.exists():
            return None

        try:
            with open(sidecar_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # _metadata 필드 제거
            data.pop("_metadata", None)

            return AnalysisRecord(**data)
        except (json.JSONDecodeError, TypeError, KeyError):
            return None

    def has_sidecar(self, video_path: Path) -> bool:
        """사이드카 파일이 존재하는지 확인합니다."""
        return self.get_sidecar_path(video_path).exists()

    def delete_sidecar(self, video_path: Path) -> bool:
        """사이드카 파일을 삭제합니다."""
        sidecar_path = self.get_sidecar_path(video_path)
        if sidecar_path.exists():
            sidecar_path.unlink()
            return True
        return False

    # =========================================================================
    # 중앙 저장소 관리 (히스토리)
    # =========================================================================

    def _load_central_store(self) -> dict:
        """중앙 저장소를 로드합니다."""
        if not self.central_store_path.exists():
            return {"records": {}}

        try:
            with open(self.central_store_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"records": {}}

    def _save_central_store(self, data: dict):
        """중앙 저장소를 저장합니다."""
        with open(self.central_store_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save_to_history(self, record: AnalysisRecord) -> str:
        """
        분석 결과를 중앙 히스토리에 저장합니다.

        Args:
            record: 분석 기록

        Returns:
            str: 레코드 ID
        """
        store = self._load_central_store()
        store["records"][record.id] = asdict(record)
        self._save_central_store(store)
        return record.id

    def get_from_history(self, record_id: str) -> Optional[AnalysisRecord]:
        """히스토리에서 특정 레코드를 조회합니다."""
        store = self._load_central_store()
        data = store.get("records", {}).get(record_id)

        if data:
            return AnalysisRecord(**data)
        return None

    def list_history(self, limit: int = 50) -> list[AnalysisRecord]:
        """
        분석 히스토리 목록을 반환합니다.

        Args:
            limit: 최대 반환 개수

        Returns:
            list[AnalysisRecord]: 최신순으로 정렬된 기록 목록
        """
        store = self._load_central_store()
        records = []

        for data in store.get("records", {}).values():
            try:
                records.append(AnalysisRecord(**data))
            except (TypeError, KeyError):
                continue

        # 최신순 정렬
        records.sort(key=lambda r: r.created_at, reverse=True)

        return records[:limit]

    def delete_from_history(self, record_id: str) -> bool:
        """히스토리에서 레코드를 삭제합니다."""
        store = self._load_central_store()

        if record_id in store.get("records", {}):
            del store["records"][record_id]
            self._save_central_store(store)
            return True
        return False

    def clear_history(self) -> int:
        """전체 히스토리를 삭제합니다."""
        store = self._load_central_store()
        count = len(store.get("records", {}))
        store["records"] = {}
        self._save_central_store(store)
        return count

    # =========================================================================
    # 영상 파일 내부 메타데이터 (FFmpeg)
    # =========================================================================

    def write_video_metadata(
        self,
        video_path: Path,
        record: AnalysisRecord,
        output_path: Optional[Path] = None,
    ) -> tuple[bool, str]:
        """
        분석 결과를 영상 파일 내부 메타데이터로 저장합니다.

        Args:
            video_path: 원본 영상 경로
            record: 분석 기록
            output_path: 출력 파일 경로 (None이면 원본 덮어쓰기)

        Returns:
            tuple[bool, str]: (성공 여부, 메시지)

        Note:
            - MP4: comment, description 필드에 저장 (표준 태그만 안정적)
            - MKV: 커스텀 태그 저장 가능
            - 긴 분석 결과는 256자로 제한
        """
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return (False, "FFmpeg를 찾을 수 없습니다.")

        video_path = Path(video_path)
        if not video_path.exists():
            return (False, f"파일을 찾을 수 없습니다: {video_path}")

        # 출력 경로 설정
        if output_path is None:
            # 임시 파일에 먼저 저장 후 교체
            temp_path = video_path.with_suffix(f".temp{video_path.suffix}")
            replace_original = True
        else:
            temp_path = Path(output_path)
            replace_original = False

        # 요약 생성 (256자 제한)
        summary = record.analysis_result[:250] + "..." if len(record.analysis_result) > 250 else record.analysis_result
        summary = summary.replace('"', "'").replace("\n", " ")

        # 파일 확장자에 따른 메타데이터 설정
        ext = video_path.suffix.lower()

        if ext == ".mkv":
            # MKV: 커스텀 태그 가능
            metadata_args = [
                "-metadata", f"ANALYSIS_ID={record.id}",
                "-metadata", f"ANALYSIS_DATE={record.created_at[:10]}",
                "-metadata", f"ANALYSIS_PROVIDER={record.ai_provider}",
                "-metadata", f"ANALYSIS_SUMMARY={summary}",
            ]
        else:
            # MP4 등: 표준 태그만 사용
            metadata_args = [
                "-metadata", f"comment=AI Analysis: {record.id}",
                "-metadata", f"description={summary}",
            ]

        cmd = [
            ffmpeg,
            "-i", str(video_path),
            "-c", "copy",  # 재인코딩 없이 복사
            "-map", "0",   # 모든 스트림 유지
            *metadata_args,
            "-y",  # 덮어쓰기
            str(temp_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                if temp_path.exists():
                    temp_path.unlink()
                return (False, f"FFmpeg 오류: {result.stderr[:200]}")

            # 원본 교체
            if replace_original:
                video_path.unlink()
                temp_path.rename(video_path)

            return (True, "메타데이터가 저장되었습니다.")

        except subprocess.TimeoutExpired:
            if temp_path.exists():
                temp_path.unlink()
            return (False, "FFmpeg 시간 초과")
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            return (False, str(e))

    def read_video_metadata(self, video_path: Path) -> Optional[dict]:
        """
        영상 파일의 메타데이터를 읽습니다.

        Args:
            video_path: 영상 파일 경로

        Returns:
            Optional[dict]: 메타데이터 딕셔너리 또는 None
        """
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            return None

        cmd = [
            ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(video_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                data = json.loads(result.stdout)
                return data.get("format", {}).get("tags", {})
        except (subprocess.TimeoutExpired, json.JSONDecodeError):
            pass

        return None

    # =========================================================================
    # 통합 저장/로드
    # =========================================================================

    def save(
        self,
        record: AnalysisRecord,
        save_sidecar: bool = True,
        save_to_history: bool = True,
        write_to_video: bool = False,
    ) -> dict:
        """
        분석 결과를 저장합니다.

        Args:
            record: 분석 기록
            save_sidecar: 사이드카 JSON 저장 여부
            save_to_history: 중앙 히스토리 저장 여부
            write_to_video: 영상 파일 내부 메타데이터 저장 여부

        Returns:
            dict: 저장 결과
        """
        results = {
            "record_id": record.id,
            "sidecar": None,
            "history": None,
            "video_metadata": None,
        }

        if save_sidecar:
            try:
                path = self.save_sidecar(record)
                results["sidecar"] = str(path)
            except Exception as e:
                results["sidecar"] = f"오류: {e}"

        if save_to_history:
            try:
                self.save_to_history(record)
                results["history"] = "저장됨"
            except Exception as e:
                results["history"] = f"오류: {e}"

        if write_to_video and record.video_path:
            success, message = self.write_video_metadata(
                Path(record.video_path),
                record,
            )
            results["video_metadata"] = message if success else f"오류: {message}"

        return results
