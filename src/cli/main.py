"""CLI 메인 모듈."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .commands import analyze_command, cache_command, history_command, status_command
from .utils import download_youtube, is_youtube_url


def create_parser() -> argparse.ArgumentParser:
    """CLI 파서 생성."""
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

    _add_analyze_parser(subparsers)
    _add_history_parser(subparsers)
    _add_cache_parser(subparsers)
    subparsers.add_parser("status", help="의존성 상태 확인")

    return parser


def _add_analyze_parser(subparsers):
    """analyze 명령어 파서 추가."""
    analyze_parser = subparsers.add_parser("analyze", help="영상 분석")
    analyze_parser.add_argument("input", help="영상 파일 경로 또는 YouTube URL")
    analyze_parser.add_argument("--interval", "-i", type=float, help="추출 간격 (초)")
    analyze_parser.add_argument(
        "--model", "-m", default="auto",
        choices=["auto", "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"],
        help="Gemini 모델 (기본: auto)",
    )
    analyze_parser.add_argument(
        "--language", "-l", default="korean",
        choices=["korean", "english", "japanese", "chinese", "auto"],
        help="출력 언어 (기본: korean)",
    )
    analyze_parser.add_argument("--prompt", "-p", help="사용자 정의 추가 프롬프트")
    analyze_parser.add_argument("--no-sidecar", action="store_true", help="사이드카 JSON 저장 안함")
    analyze_parser.add_argument("--no-history", action="store_true", help="히스토리 저장 안함")
    analyze_parser.add_argument("--keep-cache", action="store_true", help="캐시 유지")
    analyze_parser.add_argument("--json", action="store_true", help="JSON 형식으로 출력")


def _add_history_parser(subparsers):
    """history 명령어 파서 추가."""
    history_parser = subparsers.add_parser("history", help="분석 히스토리 조회")
    history_parser.add_argument("--limit", "-n", type=int, default=20, help="최대 개수 (기본: 20)")
    history_parser.add_argument("--id", help="특정 기록 ID 조회")
    history_parser.add_argument("--json", action="store_true", help="JSON 형식으로 출력")


def _add_cache_parser(subparsers):
    """cache 명령어 파서 추가."""
    cache_parser = subparsers.add_parser("cache", help="캐시 관리")
    cache_parser.add_argument(
        "action", nargs="?", default="status",
        choices=["status", "clean", "clean-old"],
        help="작업 (기본: status)",
    )
    cache_parser.add_argument("--json", action="store_true", help="JSON 형식으로 출력")


def main():
    """CLI 메인 함수."""
    parser = create_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    output_format = "json" if getattr(args, "json", False) else "text"

    if args.command == "status":
        status_command()

    elif args.command == "analyze":
        _handle_analyze(args, output_format)

    elif args.command == "history":
        _handle_history(args, output_format)

    elif args.command == "cache":
        _handle_cache(args, output_format)


def _handle_analyze(args, output_format: str):
    """analyze 명령어 처리."""
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

    result = analyze_command(
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


def _handle_history(args, output_format: str):
    """history 명령어 처리."""
    result = history_command(
        record_id=args.id,
        limit=args.limit,
        output_format=output_format,
    )

    if output_format == "json" and result:
        print(json.dumps(result, ensure_ascii=False, indent=2))


def _handle_cache(args, output_format: str):
    """cache 명령어 처리."""
    result = cache_command(args.action)

    if output_format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
