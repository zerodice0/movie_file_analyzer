#!/usr/bin/env python3
"""Movie File Analyzer CLI - Claude Code 스킬용 명령줄 인터페이스."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

# 프로젝트 루트를 PYTHONPATH에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.ai_connector import AIConnectorFactory, GeminiConnector
from src.core.context_optimizer import ContextOptimizer
from src.core.frame_extractor import FrameExtractor
from src.data.metadata_store import MetadataStore
from src.data.models import AnalysisRecord, AppConfig
from src.utils.cache_manager import CacheManager


def check_dependencies() -> dict[str, bool]:
    """의존성 설치 상태를 확인합니다."""
    import shutil

    return {
        "ffmpeg": shutil.which("ffmpeg") is not None,
        "ffprobe": shutil.which("ffprobe") is not None,
        "gemini": shutil.which("gemini") is not None,
        "yt-dlp": shutil.which("yt-dlp") is not None or shutil.which("yt_dlp") is not None,
    }


def print_status():
    """의존성 상태를 출력합니다."""
    deps = check_dependencies()

    print("\n📦 의존성 상태")
    print("=" * 50)

    for name, installed in deps.items():
        status = "✅ 설치됨" if installed else "❌ 미설치"
        required = "(필수)" if name in ["ffmpeg", "ffprobe", "gemini"] else "(선택)"
        print(f"  {name}: {status} {required}")

    print()


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
        from src.core.youtube_downloader import YouTubeDownloader

        downloader = YouTubeDownloader()
        if not downloader.is_available():
            return False, "yt-dlp가 설치되어 있지 않습니다.", None

        if output_dir is None:
            output_dir = Path.home() / ".movie_file_analyzer" / "downloads"
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"🔄 YouTube 영상 다운로드 중: {url}")

        # 진행률 콜백
        def progress_callback(progress):
            if progress.percent:
                print(f"   진행률: {progress.percent:.1f}%", end="\r")

        result = downloader.download(url, output_dir, progress_callback=progress_callback)
        print()  # 줄바꿈

        if result.success:
            return True, f"다운로드 완료: {result.file_path}", result.file_path
        else:
            return False, f"다운로드 실패: {result.error_message}", None

    except ImportError:
        return False, "YouTube 다운로더 모듈을 로드할 수 없습니다.", None
    except Exception as e:
        return False, f"다운로드 오류: {e}", None


def analyze_video(
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
        # 프레임 추출기 초기화
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

        # 캐시 매니저 초기화
        cache_manager = CacheManager(auto_cleanup=cleanup_cache)
        frames_dir = cache_manager.create_cache_dir(video_path)

        # 프레임 추출
        print(f"\n🖼️  프레임 추출 중...")
        frames = extractor.extract_frames(
            video_path,
            frames_dir,
            interval=interval,
        )
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
            store.save(
                record,
                save_sidecar=save_sidecar,
                save_to_history=save_history,
            )
            result["record_id"] = record.id

        # 캐시 정리
        if cleanup_cache:
            cache_manager.cleanup_video_cache(video_path)
            print(f"\n🗑️  캐시 정리 완료")

        print(f"\n✅ 분석 완료!")

    except Exception as e:
        result["error"] = str(e)

    return result


def list_history(limit: int = 20, output_format: str = "text") -> list[dict]:
    """분석 히스토리를 조회합니다."""
    store = MetadataStore()
    records = store.list_history(limit=limit)

    if output_format == "json":
        return [
            {
                "id": r.id,
                "video_name": r.video_name,
                "video_duration": r.video_duration,
                "frame_count": r.frame_count,
                "created_at": r.created_at,
                "analysis_preview": r.analysis_result[:200] + "..." if len(r.analysis_result) > 200 else r.analysis_result,
            }
            for r in records
        ]

    if not records:
        print("\n📭 분석 히스토리가 없습니다.")
        return []

    print(f"\n📜 분석 히스토리 (최근 {len(records)}개)")
    print("=" * 70)

    for i, record in enumerate(records, 1):
        created = record.created_datetime.strftime("%Y-%m-%d %H:%M")
        print(f"\n{i}. [{record.id[:8]}] {record.video_name}")
        print(f"   생성: {created} | 길이: {record.video_duration:.0f}초 | 프레임: {record.frame_count}개")
        preview = record.analysis_result[:100].replace("\n", " ")
        print(f"   요약: {preview}...")

    print()
    return [{"id": r.id, "video_name": r.video_name} for r in records]


def get_history_detail(record_id: str, output_format: str = "text") -> Optional[dict]:
    """특정 분석 기록의 상세 내용을 조회합니다."""
    store = MetadataStore()
    record = store.get_from_history(record_id)

    if not record:
        # 부분 ID로 검색
        records = store.list_history(limit=1000)
        for r in records:
            if r.id.startswith(record_id):
                record = r
                break

    if not record:
        print(f"\n❌ 기록을 찾을 수 없습니다: {record_id}")
        return None

    if output_format == "json":
        return {
            "id": record.id,
            "video_path": record.video_path,
            "video_name": record.video_name,
            "video_duration": record.video_duration,
            "video_resolution": record.video_resolution,
            "frame_count": record.frame_count,
            "ai_provider": record.ai_provider,
            "created_at": record.created_at,
            "analysis_result": record.analysis_result,
        }

    print(f"\n📋 분석 결과 상세")
    print("=" * 70)
    print(f"ID: {record.id}")
    print(f"파일: {record.video_name}")
    print(f"경로: {record.video_path}")
    print(f"길이: {record.video_duration:.0f}초")
    print(f"해상도: {record.video_resolution}")
    print(f"프레임: {record.frame_count}개")
    print(f"AI: {record.ai_provider}")
    print(f"생성일: {record.created_at}")
    print("\n--- 분석 결과 ---\n")
    print(record.analysis_result)
    print()

    return {"id": record.id, "analysis_result": record.analysis_result}


def manage_cache(action: str = "status") -> dict:
    """캐시를 관리합니다."""
    cache_manager = CacheManager()

    if action == "status":
        size_mb = cache_manager.get_total_size_mb()
        count = cache_manager.get_cache_count()

        print(f"\n📦 캐시 상태")
        print(f"   총 크기: {size_mb:.1f}MB")
        print(f"   캐시 수: {count}개")
        print(f"   위치: {cache_manager.cache_dir}")
        print()

        return {"size_mb": size_mb, "count": count, "path": str(cache_manager.cache_dir)}

    elif action == "clean":
        count = cache_manager.cleanup_all()
        print(f"\n🗑️  캐시 정리 완료: {count}개 삭제")
        return {"deleted": count}

    elif action == "clean-old":
        count = cache_manager.cleanup_old_cache()
        print(f"\n🗑️  오래된 캐시 정리 완료: {count}개 삭제")
        return {"deleted": count}

    return {}


def main():
    """CLI 메인 함수."""
    parser = argparse.ArgumentParser(
        description="Movie File Analyzer CLI - 영상 분석 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  # 영상 분석
  python -m src.cli analyze video.mp4
  python -m src.cli analyze video.mp4 --interval 5 --model gemini-2.5-flash
  python -m src.cli analyze "https://youtube.com/watch?v=xxx"

  # 히스토리 조회
  python -m src.cli history
  python -m src.cli history --limit 10
  python -m src.cli history --id abc12345

  # 캐시 관리
  python -m src.cli cache status
  python -m src.cli cache clean

  # 상태 확인
  python -m src.cli status
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="명령어")

    # analyze 명령어
    analyze_parser = subparsers.add_parser("analyze", help="영상 분석")
    analyze_parser.add_argument("input", help="영상 파일 경로 또는 YouTube URL")
    analyze_parser.add_argument("--interval", "-i", type=float, help="추출 간격 (초)")
    analyze_parser.add_argument("--model", "-m", default="auto",
                                choices=["auto", "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"],
                                help="Gemini 모델 (기본: auto)")
    analyze_parser.add_argument("--language", "-l", default="korean",
                                choices=["korean", "english", "japanese", "chinese", "auto"],
                                help="출력 언어 (기본: korean)")
    analyze_parser.add_argument("--prompt", "-p", help="사용자 정의 추가 프롬프트")
    analyze_parser.add_argument("--no-sidecar", action="store_true", help="사이드카 JSON 저장 안함")
    analyze_parser.add_argument("--no-history", action="store_true", help="히스토리 저장 안함")
    analyze_parser.add_argument("--keep-cache", action="store_true", help="캐시 유지")
    analyze_parser.add_argument("--json", action="store_true", help="JSON 형식으로 출력")

    # history 명령어
    history_parser = subparsers.add_parser("history", help="분석 히스토리 조회")
    history_parser.add_argument("--limit", "-n", type=int, default=20, help="최대 개수 (기본: 20)")
    history_parser.add_argument("--id", help="특정 기록 ID 조회")
    history_parser.add_argument("--json", action="store_true", help="JSON 형식으로 출력")

    # cache 명령어
    cache_parser = subparsers.add_parser("cache", help="캐시 관리")
    cache_parser.add_argument("action", nargs="?", default="status",
                              choices=["status", "clean", "clean-old"],
                              help="작업 (기본: status)")
    cache_parser.add_argument("--json", action="store_true", help="JSON 형식으로 출력")

    # status 명령어
    subparsers.add_parser("status", help="의존성 상태 확인")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    output_format = "json" if getattr(args, "json", False) else "text"

    if args.command == "status":
        print_status()

    elif args.command == "analyze":
        input_path = args.input

        # YouTube URL 처리
        if is_youtube_url(input_path):
            success, message, video_path = download_youtube(input_path)
            if not success:
                if output_format == "json":
                    print(json.dumps({"success": False, "error": message}, ensure_ascii=False))
                else:
                    print(f"❌ {message}")
                return
            print(f"✅ {message}")
        else:
            video_path = Path(input_path)

        result = analyze_video(
            video_path=video_path,
            interval=args.interval,
            model=args.model,
            language=args.language,
            custom_prompt=args.prompt,
            save_sidecar=not args.no_sidecar,
            save_history=not args.no_history,
            cleanup_cache=not args.keep_cache,
            output_format=output_format,
        )

        if output_format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif result["success"]:
            print("\n--- 분석 결과 ---\n")
            print(result["analysis"])
        else:
            print(f"\n❌ 오류: {result['error']}")

    elif args.command == "history":
        if args.id:
            result = get_history_detail(args.id, output_format)
            if output_format == "json" and result:
                print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            result = list_history(args.limit, output_format)
            if output_format == "json":
                print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "cache":
        result = manage_cache(args.action)
        if output_format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
