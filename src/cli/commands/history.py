"""히스토리 명령어."""

from __future__ import annotations

from typing import Optional

from ...data.metadata_store import MetadataStore


def history_command(
    record_id: Optional[str] = None,
    limit: int = 20,
    output_format: str = "text",
) -> list[dict] | dict | None:
    """
    분석 히스토리를 조회합니다.

    Args:
        record_id: 특정 기록 ID (None이면 목록 조회)
        limit: 최대 개수
        output_format: 출력 형식 (text/json)

    Returns:
        조회 결과
    """
    if record_id:
        return _get_history_detail(record_id, output_format)
    else:
        return _list_history(limit, output_format)


def _list_history(limit: int, output_format: str) -> list[dict]:
    """분석 히스토리 목록 조회."""
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
                "analysis_preview": (
                    r.analysis_result[:200] + "..."
                    if len(r.analysis_result) > 200
                    else r.analysis_result
                ),
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


def _get_history_detail(record_id: str, output_format: str) -> Optional[dict]:
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
