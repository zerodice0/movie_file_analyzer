"""캐시 관리 명령어."""

from __future__ import annotations

from ...utils.cache_manager import CacheManager


def cache_command(action: str = "status") -> dict:
    """
    캐시를 관리합니다.

    Args:
        action: 작업 (status/clean/clean-old)

    Returns:
        dict: 작업 결과
    """
    cache_manager = CacheManager()

    if action == "status":
        return _cache_status(cache_manager)
    elif action == "clean":
        return _cache_clean(cache_manager)
    elif action == "clean-old":
        return _cache_clean_old(cache_manager)

    return {}


def _cache_status(cache_manager: CacheManager) -> dict:
    """캐시 상태 조회."""
    size_mb = cache_manager.get_total_size_mb()
    count = cache_manager.get_cache_count()

    print(f"\n📦 캐시 상태")
    print(f"   총 크기: {size_mb:.1f}MB")
    print(f"   캐시 수: {count}개")
    print(f"   위치: {cache_manager.cache_dir}")
    print()

    return {
        "size_mb": size_mb,
        "count": count,
        "path": str(cache_manager.cache_dir),
    }


def _cache_clean(cache_manager: CacheManager) -> dict:
    """모든 캐시 삭제."""
    count = cache_manager.cleanup_all()
    print(f"\n🗑️  캐시 정리 완료: {count}개 삭제")
    return {"deleted": count}


def _cache_clean_old(cache_manager: CacheManager) -> dict:
    """오래된 캐시 삭제."""
    count = cache_manager.cleanup_old_cache()
    print(f"\n🗑️  오래된 캐시 정리 완료: {count}개 삭제")
    return {"deleted": count}
