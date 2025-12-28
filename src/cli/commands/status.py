"""상태 확인 명령어."""

from ..utils import check_dependencies


def status_command():
    """의존성 상태를 출력합니다."""
    deps = check_dependencies()

    print("\n📦 의존성 상태")
    print("=" * 50)

    for name, installed in deps.items():
        status = "✅ 설치됨" if installed else "❌ 미설치"
        required = "(필수)" if name in ["ffmpeg", "ffprobe", "gemini"] else "(선택)"
        print(f"  {name}: {status} {required}")

    print()
