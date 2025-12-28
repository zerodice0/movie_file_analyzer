---
name: movie-file-analyzer
description: 영상 파일을 분석하여 내용을 텍스트로 요약하는 스킬. 영상 분석, 동영상 분석, 비디오 분석, YouTube 영상 다운로드 및 분석, 영상 내용 파악, 분석 히스토리 조회를 요청할 때 사용됩니다.
---

# Movie File Analyzer Skill

영상 파일에서 I-Frame을 추출하고 Google Gemini AI로 분석하여 내용을 텍스트로 요약하는 도구입니다.

## 기능

1. **영상 분석**: 로컬 영상 파일 또는 YouTube URL의 영상을 AI로 분석
2. **히스토리 조회**: 이전 분석 기록 조회
3. **캐시 관리**: 추출된 프레임 캐시 관리

## 사용 전 확인사항

이 스킬을 사용하기 전에 다음 의존성이 설치되어 있어야 합니다:
- FFmpeg (필수): 프레임 추출에 사용
- Gemini CLI (필수): AI 분석에 사용
- yt-dlp (선택): YouTube 영상 다운로드에 사용

의존성 상태를 확인하려면:
```bash
cd ~/path/to/movie_file_analyzer && python -m src.cli status
```

## 사용법

### 1. 영상 분석

로컬 영상 파일 분석:
```bash
cd /home/user/movie_file_analyzer && python -m src.cli analyze /path/to/video.mp4
```

추출 간격과 모델 지정:
```bash
cd /home/user/movie_file_analyzer && python -m src.cli analyze /path/to/video.mp4 --interval 5 --model gemini-2.5-flash
```

YouTube 영상 분석:
```bash
cd /home/user/movie_file_analyzer && python -m src.cli analyze "https://youtube.com/watch?v=VIDEO_ID"
```

### 2. 분석 옵션

- `--interval`, `-i`: 프레임 추출 간격 (초). 미지정 시 자동 계산
- `--model`, `-m`: Gemini 모델 선택
  - `auto`: 자동 선택 (기본값)
  - `gemini-2.5-pro`: 안정적이고 정확함 (권장)
  - `gemini-2.5-flash`: 빠른 분석
  - `gemini-2.0-flash`: 경량 분석
- `--language`, `-l`: 출력 언어
  - `korean`: 한국어 (기본값)
  - `english`: English
  - `japanese`: 日本語
  - `chinese`: 中文
  - `auto`: 자동
- `--prompt`, `-p`: 사용자 정의 추가 프롬프트
- `--json`: JSON 형식으로 출력

### 3. 히스토리 조회

최근 분석 기록 보기:
```bash
cd /home/user/movie_file_analyzer && python -m src.cli history
```

최근 10개만 보기:
```bash
cd /home/user/movie_file_analyzer && python -m src.cli history --limit 10
```

특정 기록 상세 보기 (ID의 처음 8자리 사용 가능):
```bash
cd /home/user/movie_file_analyzer && python -m src.cli history --id abc12345
```

### 4. 캐시 관리

캐시 상태 확인:
```bash
cd /home/user/movie_file_analyzer && python -m src.cli cache status
```

모든 캐시 삭제:
```bash
cd /home/user/movie_file_analyzer && python -m src.cli cache clean
```

오래된 캐시만 삭제:
```bash
cd /home/user/movie_file_analyzer && python -m src.cli cache clean-old
```

## 분석 결과 형식

분석 결과는 다음 형식으로 제공됩니다:

```
## 영상 요약
(전체 영상의 주제와 내용을 3-5문장으로 요약)

## 주요 내용
(영상의 핵심 메시지나 정보를 글머리 기호로 정리)

## 세부 사항
- **등장 요소**: 주요 인물, 장소, 물체 등
- **화면 텍스트**: 영상에 표시된 주요 텍스트
- **분위기**: 영상의 전반적인 톤과 느낌
```

## 분석 결과 저장 위치

- **JSON 사이드카**: 영상 파일 옆에 `.analysis.json` 파일로 저장
- **중앙 히스토리**: `~/.movie_file_analyzer/analysis_history.json`에 저장
- **캐시**: `~/.movie_file_analyzer/cache/`에 임시 저장

## 주의사항

1. 영상 길이에 따라 분석 시간이 달라집니다 (보통 1-5분 소요)
2. 긴 영상은 자동으로 추출 간격이 조정됩니다
3. YouTube 영상은 먼저 다운로드된 후 분석됩니다
4. 분석 후 기본적으로 캐시가 자동 삭제됩니다

## 문제 해결

### FFmpeg 설치
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

### Gemini CLI 설치
```bash
npm install -g @google/gemini-cli
```

### yt-dlp 설치
```bash
pip install yt-dlp
# 또는
brew install yt-dlp
```

## 예시

사용자가 "이 영상 분석해줘"라고 요청하면:
1. 먼저 의존성이 설치되어 있는지 확인
2. 영상 경로를 확인하고 분석 명령 실행
3. 분석 결과를 사용자에게 전달
