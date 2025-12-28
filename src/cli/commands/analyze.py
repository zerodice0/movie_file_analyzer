"""분석 명령어."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..utils import check_dependencies
from ...core.ai_connector import AIConnectorFactory
from ...core.context_optimizer import ContextOptimizer
from ...core.frame_extractor import FrameExtractor
from ...data.metadata_store import MetadataStore
from ...data.models import AnalysisRecord
from ...utils.cache_manager import CacheManager


def analyze_command(
    video_path: Path,
    interval: Optional[float] = None,
    model: str = "auto",
    language: str = "korean",
    custom_prompt: Optional[str] = None,
    save_sidecar: bool = True,
    save_history: bool = True,
    cleanup_cache: bool = True,
    output_format: str = "text",
) -> dict:
    """
    영상을 분석합니다.

    Args:
        video_path: 영상 파일 경로
        interval: 추출 간격 (초), None이면 자동 계산
        model: Gemini 모델
        language: 출력 언어
        custom_prompt: 사용자 정의 프롬프트
        save_sidecar: 사이드카 JSON 저장 여부
        save_history: 히스토리 저장 여부
        cleanup_cache: 분석 후 캐시 정리 여부
        output_format: 출력 형식 (text/json)

    Returns:
        dict: 분석 결과
    """
    result = {
        "success": False,
        "video_path": str(video_path),
        "analysis": "",
        "error": None,
        "metadata": {},
    }

    # 의존성 확인
    deps = check_dependencies()
    if not deps["ffmpeg"] or not deps["ffprobe"]:
        result["error"] = "FFmpeg가 설치되어 있지 않습니다."
        return result

    if not deps["gemini"]:
        result["error"] = "Gemini CLI가 설치되어 있지 않습니다."
        return result

    if not video_path.exists():
        result["error"] = f"파일을 찾을 수 없습니다: {video_path}"
        return result

    try:
        result = _perform_analysis(
            video_path, interval, model, language,
            custom_prompt, save_sidecar, save_history, cleanup_cache
        )
    except Exception as e:
        result["error"] = str(e)

    return result


def _perform_analysis(
    video_path: Path,
    interval: Optional[float],
    model: str,
    language: str,
    custom_prompt: Optional[str],
    save_sidecar: bool,
    save_history: bool,
    cleanup_cache: bool,
) -> dict:
    """실제 분석 수행."""
    result = {
        "success": False,
        "video_path": str(video_path),
        "analysis": "",
        "error": None,
        "metadata": {},
    }

    extractor = FrameExtractor()
    video_info = extractor.get_video_info(video_path)

    print(f"\n📹 영상 정보")
    print(f"   파일: {video_path.name}")
    print(f"   길이: {video_info.duration_str}")
    print(f"   해상도: {video_info.width}x{video_info.height}")
    print(f"   크기: {video_info.size_mb:.1f}MB")

    # 추출 간격 자동 계산
    if interval is None:
        optimizer = ContextOptimizer()
        strategy = optimizer.calculate_strategy(video_info.duration)
        interval = strategy.interval_seconds
        print(f"\n🔧 자동 최적화")
        print(f"   추출 간격: {interval}초")
        print(f"   예상 프레임: {strategy.estimated_frames}개")

    # 캐시 및 프레임 추출
    cache_manager = CacheManager(auto_cleanup=cleanup_cache)
    frames_dir = cache_manager.create_cache_dir(video_path)

    print(f"\n🖼️  프레임 추출 중...")
    frames = extractor.extract_frames(video_path, frames_dir, interval=interval)
    print(f"   추출 완료: {len(frames)}개 프레임")

    # AI 분석
    print(f"\n🤖 AI 분석 중 (모델: {model})...")
    connector = AIConnectorFactory.create("gemini", model=model)
    analysis_result = connector.analyze(
        frame_paths=frames,
        interval_sec=interval,
        duration_str=video_info.duration_str,
        custom_prompt=custom_prompt,
        output_language=language,
        working_dir=frames_dir,
    )

    if not analysis_result.success:
        result["error"] = analysis_result.error_message
        return result

    # 결과 구성
    result["success"] = True
    result["analysis"] = analysis_result.result
    result["metadata"] = {
        "video_name": video_path.name,
        "video_duration": video_info.duration,
        "video_resolution": f"{video_info.width}x{video_info.height}",
        "frame_count": len(frames),
        "interval_seconds": interval,
        "model": model,
        "language": language,
    }

    # 분석 기록 저장
    if save_sidecar or save_history:
        _save_record(
            video_path, video_info, interval, frames,
            analysis_result, save_sidecar, save_history
        )
        result["record_id"] = None  # record.id를 별도로 얻을 수 있음

    # 캐시 정리
    if cleanup_cache:
        cache_manager.cleanup_video_cache(video_path)
        print(f"\n🗑️  캐시 정리 완료")

    print(f"\n✅ 분석 완료!")
    return result


def _save_record(
    video_path: Path,
    video_info,
    interval: float,
    frames: list,
    analysis_result,
    save_sidecar: bool,
    save_history: bool,
):
    """분석 기록 저장."""
    record = AnalysisRecord(
        video_path=str(video_path),
        video_name=video_path.name,
        video_duration=video_info.duration,
        video_resolution=(video_info.width, video_info.height),
        video_size_mb=video_info.size_mb,
        extraction_mode="interval" if interval else "all_iframes",
        extraction_interval=interval,
        frame_count=len(frames),
        ai_provider="Gemini",
        prompt_used=analysis_result.prompt_used,
        analysis_result=analysis_result.result,
    )

    store = MetadataStore()
    store.save(record, save_sidecar=save_sidecar, save_to_history=save_history)
