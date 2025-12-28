"""AI CLI 도구 연동 모듈 (Gemini CLI 전용)."""

from __future__ import annotations

import logging
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# 디버깅용 로거 설정
logger = logging.getLogger(__name__)


# Gemini 지원 모델 목록 (2025년 12월 기준)
# Note: gemini-3-*-preview 모델은 CLI 0.21.1+ 및 Preview 설정 활성화 필요
GEMINI_MODELS = {
    "auto": "자동 (기본값)",
    "gemini-3-pro-preview": "Gemini 3 Pro (최신, 고성능, Preview)",
    "gemini-3-flash-preview": "Gemini 3 Flash (최신, 빠름, Preview)",
    "gemini-2.5-pro": "Gemini 2.5 Pro (안정, 권장)",
    "gemini-2.5-flash": "Gemini 2.5 Flash (빠름)",
    "gemini-2.0-flash": "Gemini 2.0 Flash (경량)",
}


@dataclass
class AnalysisResult:
    """AI 분석 결과."""

    provider: str
    result: str
    prompt_used: str
    frame_count: int
    success: bool
    error_message: Optional[str] = None
    model_used: Optional[str] = None


class AIConnector(ABC):
    """AI CLI 도구 연동을 위한 추상 기본 클래스."""

    # 기본 프롬프트 템플릿 (개선됨: 전체 영상 요약 유도)
    DEFAULT_PROMPT_TEMPLATE = """다음은 영상에서 {interval_desc}으로 추출한 연속 프레임 {frame_count}개입니다.
영상 전체 길이는 {duration}입니다.

**중요**: 이 프레임들은 하나의 연속된 영상에서 추출한 것입니다.
개별 프레임을 따로 분석하지 말고, 전체 영상의 흐름과 서사를 파악하여 통합적으로 요약해주세요.

다음 형식으로 응답해주세요:

## 영상 요약
(전체 영상의 주제와 내용을 3-5문장으로 요약)

## 주요 내용
(영상의 핵심 메시지나 정보를 글머리 기호로 정리)

## 세부 사항
- **등장 요소**: 주요 인물, 장소, 물체 등
- **화면 텍스트**: 영상에 표시된 주요 텍스트 (있는 경우)
- **분위기**: 영상의 전반적인 톤과 느낌

**주의**: "Frame 1", "Frame 2" 등 개별 프레임 번호를 언급하지 마세요.
영상 전체의 서사적 흐름에 집중해주세요.

{language_instruction}"""

    @abstractmethod
    def get_command_name(self) -> str:
        """CLI 명령어 이름을 반환합니다."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """제공자 이름을 반환합니다."""
        pass

    @abstractmethod
    def _build_command(
        self,
        prompt: str,
        frame_paths: list[Path],
    ) -> list[str]:
        """CLI 명령어를 구성합니다."""
        pass

    def is_available(self) -> bool:
        """CLI 도구가 설치되어 있는지 확인합니다."""
        return shutil.which(self.get_command_name()) is not None

    def build_prompt(
        self,
        interval_sec: Optional[float],
        frame_count: int,
        duration_str: str,
        custom_prompt: Optional[str] = None,
        output_language: str = "korean",
    ) -> str:
        """
        분석용 프롬프트를 생성합니다.

        Args:
            interval_sec: 추출 간격 (초), None이면 I-Frame 추출
            frame_count: 프레임 수
            duration_str: 영상 길이 문자열
            custom_prompt: 사용자 정의 추가 프롬프트
            output_language: 출력 언어 (korean, english, japanese, chinese, auto)

        Returns:
            str: 완성된 프롬프트
        """
        from ..data.models import AppConfig

        if interval_sec is not None:
            interval_desc = f"{int(interval_sec)}초 간격"
        else:
            interval_desc = "I-Frame 기준"

        # 언어 지시문 가져오기
        language_options = AppConfig.get_language_options()
        language_instruction = language_options.get(output_language, "")

        prompt = self.DEFAULT_PROMPT_TEMPLATE.format(
            interval_desc=interval_desc,
            frame_count=frame_count,
            duration=duration_str,
            language_instruction=language_instruction,
        )

        if custom_prompt:
            prompt += f"\n\n**추가 요청**: {custom_prompt}"

        return prompt

    def analyze(
        self,
        frame_paths: list[Path],
        interval_sec: Optional[float],
        duration_str: str,
        custom_prompt: Optional[str] = None,
        output_language: str = "korean",
        timeout: int = 600,
        working_dir: Optional[Path] = None,
    ) -> AnalysisResult:
        """
        프레임을 분석합니다.

        Args:
            frame_paths: 프레임 파일 경로 목록
            interval_sec: 추출 간격 (초)
            duration_str: 영상 길이 문자열
            custom_prompt: 사용자 정의 추가 프롬프트
            output_language: 출력 언어 (korean, english, japanese, chinese, auto)
            timeout: 타임아웃 (초)
            working_dir: 작업 디렉토리 (세션 격리를 위해 사용)

        Returns:
            AnalysisResult: 분석 결과
        """
        if not self.is_available():
            return AnalysisResult(
                provider=self.get_provider_name(),
                result="",
                prompt_used="",
                frame_count=len(frame_paths),
                success=False,
                error_message=f"{self.get_command_name()} CLI를 찾을 수 없습니다.",
            )

        prompt = self.build_prompt(
            interval_sec=interval_sec,
            frame_count=len(frame_paths),
            duration_str=duration_str,
            custom_prompt=custom_prompt,
            output_language=output_language,
        )

        cmd = self._build_command(prompt, frame_paths)

        # 디버깅: 실행할 명령어 로깅
        logger.info("=" * 60)
        logger.info("[AI Connector] 명령어 실행 시작")
        logger.info(f"  명령어: {' '.join(cmd[:3])}...")  # 앞 3개만 (프롬프트는 너무 길어서 생략)
        logger.info(f"  프레임 수: {len(frame_paths)}")
        logger.info(f"  작업 디렉토리: {working_dir}")

        try:
            # working_dir이 지정되면 해당 디렉토리에서 실행 (세션 격리)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(working_dir) if working_dir else None,
            )

            # 디버깅: 실행 결과 로깅
            logger.info(f"  반환 코드: {result.returncode}")
            logger.info(f"  stdout 길이: {len(result.stdout) if result.stdout else 0}")
            logger.info(f"  stderr 길이: {len(result.stderr) if result.stderr else 0}")
            if result.stderr:
                logger.warning(f"  stderr 내용: {result.stderr[:500]}")

            if result.returncode != 0:
                logger.error(f"[AI Connector] 명령어 실패 (returncode={result.returncode})")
                return AnalysisResult(
                    provider=self.get_provider_name(),
                    result="",
                    prompt_used=prompt,
                    frame_count=len(frame_paths),
                    success=False,
                    error_message=result.stderr or "알 수 없는 오류가 발생했습니다.",
                )

            # 빈 응답 검증 - AI가 빈 결과를 반환하면 실패로 처리
            output = result.stdout.strip() if result.stdout else ""
            if not output:
                error_detail = result.stderr.strip() if result.stderr else "응답 없음"
                # stderr가 너무 길면 잘라서 표시
                error_preview = error_detail[:200] if error_detail else "알 수 없음"
                logger.error(f"[AI Connector] 빈 응답 반환됨. stderr: {error_detail[:500]}")
                return AnalysisResult(
                    provider=self.get_provider_name(),
                    result="",
                    prompt_used=prompt,
                    frame_count=len(frame_paths),
                    success=False,
                    error_message=f"AI가 빈 응답을 반환했습니다. 다시 시도해주세요.\n상세: {error_preview}",
                )

            return AnalysisResult(
                provider=self.get_provider_name(),
                result=output,
                prompt_used=prompt,
                frame_count=len(frame_paths),
                success=True,
            )

        except subprocess.TimeoutExpired:
            return AnalysisResult(
                provider=self.get_provider_name(),
                result="",
                prompt_used=prompt,
                frame_count=len(frame_paths),
                success=False,
                error_message=f"분석 시간 초과 ({timeout}초)",
            )
        except Exception as e:
            return AnalysisResult(
                provider=self.get_provider_name(),
                result="",
                prompt_used=prompt,
                frame_count=len(frame_paths),
                success=False,
                error_message=str(e),
            )


class GeminiConnector(AIConnector):
    """Gemini CLI 연동."""

    def __init__(
        self,
        auto_approve: bool = True,
        clear_sessions: bool = True,
        model: str = "auto",
    ):
        """
        Args:
            auto_approve: 자동 승인 모드 (-y 플래그) 사용 여부
            clear_sessions: 분석 전 기존 세션 삭제 여부
            model: 사용할 모델 ("auto", "gemini-3-pro", "gemini-2.5-flash" 등)
        """
        self.auto_approve = auto_approve
        self.clear_sessions = clear_sessions
        self.model = model

    def get_command_name(self) -> str:
        return "gemini"

    def get_provider_name(self) -> str:
        return "Gemini"

    def _clear_all_sessions(self, working_dir: Optional[Path] = None):
        """기존 Gemini 세션을 모두 삭제합니다."""
        try:
            # 세션 목록 조회
            list_result = subprocess.run(
                ["gemini", "--list-sessions"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(working_dir) if working_dir else None,
            )

            if list_result.returncode == 0 and "Available sessions" in list_result.stdout:
                # 세션이 있으면 모두 삭제 (1부터 순차적으로)
                for i in range(1, 20):  # 최대 20개 세션까지 삭제 시도
                    delete_result = subprocess.run(
                        ["gemini", "--delete-session", str(i)],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        cwd=str(working_dir) if working_dir else None,
                    )
                    if delete_result.returncode != 0:
                        break  # 더 이상 세션이 없으면 중단
        except Exception:
            pass  # 세션 삭제 실패해도 분석 계속 진행

    def analyze(
        self,
        frame_paths: list[Path],
        interval_sec: Optional[float],
        duration_str: str,
        custom_prompt: Optional[str] = None,
        output_language: str = "korean",
        timeout: int = 600,
        working_dir: Optional[Path] = None,
    ) -> AnalysisResult:
        """Gemini로 프레임을 분석합니다. 세션 캐싱 문제 방지를 위해 세션을 먼저 정리합니다."""
        # 세션 정리 (캐싱 문제 방지)
        if self.clear_sessions:
            self._clear_all_sessions(working_dir)

        # 부모 클래스의 analyze 호출
        result = super().analyze(
            frame_paths=frame_paths,
            interval_sec=interval_sec,
            duration_str=duration_str,
            custom_prompt=custom_prompt,
            output_language=output_language,
            timeout=timeout,
            working_dir=working_dir,
        )

        # 사용된 모델 정보 추가
        result.model_used = self.model if self.model != "auto" else "auto"
        return result

    def _build_command(
        self,
        prompt: str,
        frame_paths: list[Path],
    ) -> list[str]:
        """
        Gemini CLI 명령어를 구성합니다.

        형식: gemini [--model MODEL] "프롬프트 @file1.jpg @file2.jpg ..." -y

        Note:
            Gemini CLI는 @ 접두사로 파일을 참조합니다.
            명령줄 길이 제한으로 인해 많은 파일은 처리가 어려울 수 있습니다.
        """
        # @ 접두사로 파일 참조
        file_refs = " ".join([f"@{p}" for p in frame_paths])
        full_prompt = f"{prompt}\n\n파일들: {file_refs}"

        cmd = ["gemini"]

        # 모델 지정 (auto가 아닌 경우)
        if self.model and self.model != "auto":
            cmd.extend(["--model", self.model])

        cmd.append(full_prompt)

        if self.auto_approve:
            cmd.append("-y")

        return cmd

    @staticmethod
    def get_available_models() -> dict[str, str]:
        """사용 가능한 모델 목록 반환."""
        return GEMINI_MODELS.copy()


class AIConnectorFactory:
    """AI 연결자 팩토리 (Gemini 전용)."""

    @classmethod
    def create(cls, provider: str = "gemini", model: str = "auto", **kwargs) -> AIConnector:
        """
        AI 연결자 인스턴스를 생성합니다.

        Args:
            provider: 제공자 이름 ("gemini"만 지원)
            model: Gemini 모델 이름
            **kwargs: 추가 인자

        Returns:
            AIConnector: 연결자 인스턴스

        Raises:
            ValueError: 지원하지 않는 제공자
        """
        if provider.lower() != "gemini":
            raise ValueError(
                f"지원하지 않는 제공자: {provider}. 현재 gemini만 지원됩니다."
            )
        return GeminiConnector(model=model, **kwargs)

    @classmethod
    def get_available_providers(cls) -> list[str]:
        """설치된 CLI 도구 목록을 반환합니다."""
        connector = GeminiConnector()
        if connector.is_available():
            return ["gemini"]
        return []

    @classmethod
    def get_all_providers(cls) -> list[str]:
        """모든 지원 제공자 목록을 반환합니다."""
        return ["gemini"]

    @classmethod
    def get_available_models(cls) -> dict[str, str]:
        """사용 가능한 모델 목록을 반환합니다."""
        return GeminiConnector.get_available_models()
