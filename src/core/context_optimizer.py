"""AI 컨텍스트 제한에 따른 추출 간격 최적화 모듈."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AIProvider(Enum):
    """지원하는 AI 제공자."""

    CLAUDE = "claude"
    GEMINI = "gemini"


@dataclass
class ExtractionStrategy:
    """프레임 추출 전략."""

    mode: str  # "all_iframes" | "interval"
    interval: Optional[float]  # 추출 간격 (초), None이면 모든 I-Frame
    estimated_frames: int  # 예상 프레임 수
    description: str  # 사용자에게 보여줄 설명

    @property
    def is_iframes_mode(self) -> bool:
        return self.mode == "all_iframes"


@dataclass
class ProviderLimits:
    """AI 제공자별 제한사항."""

    max_images: int  # API 최대 이미지 수
    recommended_images: int  # 권장 이미지 수
    max_image_size_mb: float  # 단일 이미지 최대 크기
    tokens_per_image: int  # 이미지당 예상 토큰 수
    description: str


class ContextOptimizer:
    """영상 길이와 AI 제공자에 따른 최적 추출 전략을 계산합니다."""

    # AI 제공자별 제한사항
    PROVIDER_LIMITS: dict[AIProvider, ProviderLimits] = {
        AIProvider.CLAUDE: ProviderLimits(
            max_images=100,
            recommended_images=80,
            max_image_size_mb=5.0,
            tokens_per_image=1500,  # 약 1000x1000px 기준
            description="Claude (최대 100장, 권장 80장)",
        ),
        AIProvider.GEMINI: ProviderLimits(
            max_images=3600,
            recommended_images=200,  # 토큰 비용 고려
            max_image_size_mb=100.0,
            tokens_per_image=258,  # 작은 이미지 기준 (고정)
            description="Gemini (최대 3600장, 권장 200장)",
        ),
    }

    # 깔끔한 간격 값 (초)
    NICE_INTERVALS = [1, 2, 3, 5, 10, 15, 20, 30, 60]

    def __init__(self, average_iframes_per_second: float = 1 / 3):
        """
        Args:
            average_iframes_per_second: 평균 I-Frame 빈도 (기본: 3초당 1개)
        """
        self.avg_iframes_per_sec = average_iframes_per_second

    def get_provider_limits(self, provider: AIProvider) -> ProviderLimits:
        """AI 제공자의 제한사항을 반환합니다."""
        return self.PROVIDER_LIMITS[provider]

    def estimate_iframes(self, duration_sec: float) -> int:
        """영상의 예상 I-Frame 수를 계산합니다."""
        return int(duration_sec * self.avg_iframes_per_sec)

    def _round_to_nice_interval(self, interval: float) -> float:
        """간격을 깔끔한 값으로 반올림합니다."""
        # 가장 가까운 깔끔한 간격 찾기
        return min(self.NICE_INTERVALS, key=lambda x: abs(x - interval))

    def calculate_strategy(
        self,
        duration_sec: float,
        provider: AIProvider,
        estimated_iframes: Optional[int] = None,
    ) -> ExtractionStrategy:
        """
        영상 길이와 AI 제공자에 따른 최적 추출 전략을 계산합니다.

        Args:
            duration_sec: 영상 길이 (초)
            provider: AI 제공자
            estimated_iframes: 예상 I-Frame 수 (None이면 자동 계산)

        Returns:
            ExtractionStrategy: 추출 전략
        """
        limits = self.PROVIDER_LIMITS[provider]
        max_frames = limits.recommended_images

        # 예상 I-Frame 수 계산
        if estimated_iframes is None:
            estimated_iframes = self.estimate_iframes(duration_sec)

        # 모든 I-Frame을 추출해도 제한 이내인 경우
        if estimated_iframes <= max_frames:
            return ExtractionStrategy(
                mode="all_iframes",
                interval=None,
                estimated_frames=estimated_iframes,
                description=f"모든 I-Frame 추출 (약 {estimated_iframes}장)",
            )

        # 간격 기반 추출 필요
        # 목표 프레임 수에 맞는 간격 계산
        ideal_interval = duration_sec / max_frames

        # 최소 1초, 최대 60초로 제한
        ideal_interval = max(1.0, min(60.0, ideal_interval))

        # 깔끔한 간격으로 반올림
        interval = self._round_to_nice_interval(ideal_interval)

        # 실제 예상 프레임 수
        estimated = int(duration_sec / interval)

        return ExtractionStrategy(
            mode="interval",
            interval=interval,
            estimated_frames=estimated,
            description=f"{int(interval)}초 간격 추출 (약 {estimated}장)",
        )

    def get_preset_strategies(
        self,
        duration_sec: float,
        provider: AIProvider,
    ) -> dict[str, ExtractionStrategy]:
        """
        사전 정의된 전략 옵션을 제공합니다.

        Args:
            duration_sec: 영상 길이 (초)
            provider: AI 제공자

        Returns:
            dict[str, ExtractionStrategy]: 전략 이름과 전략 객체 매핑
        """
        strategies = {}

        # 상세 (2초 간격)
        if duration_sec >= 4:  # 최소 2장 이상
            estimated = int(duration_sec / 2)
            strategies["상세 (2초 간격)"] = ExtractionStrategy(
                mode="interval",
                interval=2.0,
                estimated_frames=estimated,
                description=f"2초 간격 (약 {estimated}장)",
            )

        # 표준 (5초 간격)
        if duration_sec >= 10:
            estimated = int(duration_sec / 5)
            strategies["표준 (5초 간격)"] = ExtractionStrategy(
                mode="interval",
                interval=5.0,
                estimated_frames=estimated,
                description=f"5초 간격 (약 {estimated}장)",
            )

        # 간략 (10초 간격)
        if duration_sec >= 20:
            estimated = int(duration_sec / 10)
            strategies["간략 (10초 간격)"] = ExtractionStrategy(
                mode="interval",
                interval=10.0,
                estimated_frames=estimated,
                description=f"10초 간격 (약 {estimated}장)",
            )

        # 모든 I-Frame
        estimated_iframes = self.estimate_iframes(duration_sec)
        limits = self.PROVIDER_LIMITS[provider]

        if estimated_iframes <= limits.max_images:
            strategies["모든 I-Frame"] = ExtractionStrategy(
                mode="all_iframes",
                interval=None,
                estimated_frames=estimated_iframes,
                description=f"모든 I-Frame (약 {estimated_iframes}장)",
            )

        # 자동 (추천)
        auto_strategy = self.calculate_strategy(duration_sec, provider)
        strategies["자동 (추천)"] = auto_strategy

        return strategies

    def validate_strategy(
        self,
        strategy: ExtractionStrategy,
        provider: AIProvider,
    ) -> tuple[bool, str]:
        """
        전략이 제공자의 제한을 초과하는지 검증합니다.

        Args:
            strategy: 검증할 전략
            provider: AI 제공자

        Returns:
            tuple[bool, str]: (유효 여부, 메시지)
        """
        limits = self.PROVIDER_LIMITS[provider]

        if strategy.estimated_frames > limits.max_images:
            return (
                False,
                f"이미지 수({strategy.estimated_frames}장)가 "
                f"{provider.value}의 최대 허용({limits.max_images}장)을 초과합니다.",
            )

        if strategy.estimated_frames > limits.recommended_images:
            return (
                True,
                f"이미지 수({strategy.estimated_frames}장)가 권장 "
                f"({limits.recommended_images}장)을 초과합니다. "
                "토큰 사용량이 증가할 수 있습니다.",
            )

        return (True, "적정 범위입니다.")

    def estimate_tokens(
        self,
        frame_count: int,
        provider: AIProvider,
    ) -> int:
        """
        예상 토큰 사용량을 계산합니다.

        Args:
            frame_count: 프레임 수
            provider: AI 제공자

        Returns:
            int: 예상 토큰 수
        """
        limits = self.PROVIDER_LIMITS[provider]
        return frame_count * limits.tokens_per_image
