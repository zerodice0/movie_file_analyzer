# 🎬 Movie File Analyzer

```
    __  ___           _         _______ __        ___                __
   /  |/  /___ _   __(_)__     / ____(_) /__     /   |  ____  ____ _/ /_  ______  ___  _____
  / /|_/ / __ \ | / / / _ \   / /_  / / / _ \   / /| | / __ \/ __ `/ / / / /_  / / _ \/ ___/
 / /  / / /_/ / |/ / /  __/  / __/ / / /  __/  / ___ |/ / / / /_/ / / /_/ / / /_/  __/ /
/_/  /_/\____/|___/_/\___/  /_/   /_/_/\___/  /_/  |_/_/ /_/\__,_/_/\__, / /___/\___/_/
                                                                   /____/
```

> **영상에서 I-Frame을 추출하고 AI로 내용을 텍스트화하는 GUI 도구**

## ✨ 주요 기능

- 📹 **I-Frame 추출**: FFmpeg를 사용하여 영상에서 키프레임 자동 추출
- 🤖 **AI 분석**: Gemini CLI를 통해 영상 내용 분석 (모델 선택 지원)
- 📥 **YouTube 다운로드**: URL 입력만으로 YouTube 영상 다운로드 및 분석
- ⚡ **스마트 최적화**: 영상 길이와 AI 제한에 맞춘 자동 추출 간격 계산
- 📦 **의존성 관리**: 필요한 도구 자동 설치 지원 (ffmpeg, gemini-cli, yt-dlp)
- 🗑️ **캐시 관리**: 분석 후 자동 정리, 수동 정리 지원
- 🎨 **GUI 인터페이스**: PySide6 기반의 직관적인 데스크톱 앱

## 📋 요구사항

### 필수
- Python 3.11+
- FFmpeg (프레임 추출)
- [Gemini CLI](https://github.com/google-gemini/gemini-cli) - AI 분석
- macOS / Linux / Windows

### 선택
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube 다운로드
- [fzf](https://github.com/junegunn/fzf) - 인터랙티브 메뉴 및 설정

## 🚀 빠른 시작

### 1. 설치

```bash
# 저장소 클론
git clone <repository-url>
cd movie_file_analyzer

# 의존성 자동 설치 (권장)
./run.sh --install
```

또는 수동 설치:

```bash
# FFmpeg 설치 (macOS)
brew install ffmpeg

# Gemini CLI 설치
npm install -g @google/gemini-cli

# yt-dlp 설치 (선택, YouTube 다운로드용)
pip install --user yt-dlp
# 또는
brew install yt-dlp

# fzf 설치 (선택, 인터랙티브 메뉴용)
brew install fzf
```

### 2. 실행

```bash
# 실행 (자동으로 가상환경 생성 및 의존성 설치)
./run.sh
```

## 📖 사용법

### 실행 스크립트 옵션

```bash
./run.sh              # 메뉴 표시 (fzf 필요)
./run.sh --run        # 바로 앱 실행
./run.sh --config     # 환경 설정
./run.sh --clean      # 캐시 정리
./run.sh --status     # 의존성 상태 확인
./run.sh --install    # 누락된 의존성 설치
./run.sh --help       # 도움말
```

### GUI 사용법

1. **영상 선택**:
   - "찾아보기" 버튼으로 로컬 영상 파일 선택
   - 또는 YouTube URL 입력 후 "다운로드" 버튼 클릭
2. **설정 확인**: Gemini 모델과 추출 간격 확인/수정
3. **분석 시작**: "분석 시작" 버튼 클릭
4. **결과 확인**: 분석 결과를 복사하거나 저장

### 환경 변수

| 변수 | 설명 | 기본값 |
|-----|------|-------|
| `MFA_DEFAULT_MODEL` | Gemini 모델 | `auto` |
| `MFA_AUTO_CLEANUP` | 분석 후 자동 캐시 정리 | `true` |
| `MFA_MAX_CACHE_MB` | 최대 캐시 크기 (MB) | `1024` |
| `MFA_DEFAULT_INTERVAL` | 기본 추출 간격 | `auto` |

### 지원 Gemini 모델

| 모델 | 설명 |
|-----|------|
| `auto` | 자동 선택 (기본값) |
| `gemini-2.5-pro` | Gemini 2.5 Pro (안정, 권장) |
| `gemini-2.5-flash` | Gemini 2.5 Flash (빠름) |
| `gemini-2.0-flash` | Gemini 2.0 Flash (경량) |

## 🏗️ 프로젝트 구조

```
movie_file_analyzer/
├── src/
│   ├── main.py                    # 엔트리포인트
│   ├── core/
│   │   ├── frame_extractor.py     # FFmpeg I-Frame 추출
│   │   ├── context_optimizer.py   # 추출 간격 최적화
│   │   ├── ai_connector.py        # Gemini CLI 연동
│   │   └── youtube_downloader.py  # YouTube 다운로드
│   ├── ui/
│   │   ├── main_window.py         # PySide6 GUI
│   │   ├── panels.py              # UI 패널 컴포넌트
│   │   ├── worker.py              # 분석 워커
│   │   └── download_worker.py     # 다운로드 워커
│   ├── data/
│   │   ├── models.py              # 데이터 모델
│   │   └── metadata_store.py      # 메타데이터 저장
│   └── utils/
│       └── cache_manager.py       # 캐시 관리
├── run.sh                         # 실행 스크립트 (의존성 관리 포함)
├── pyproject.toml                 # 프로젝트 설정
└── README.md
```

## ⚙️ 작동 원리

### 1. I-Frame 추출

```bash
# 간격 기반 추출 (예: 5초 간격)
ffmpeg -i input.mp4 -vf "fps=1/5,scale='min(1280,iw):-2'" -vsync vfr frame_%04d.jpg

# 모든 I-Frame 추출
ffmpeg -i input.mp4 -vf "select='eq(pict_type,I)',scale='min(1280,iw):-2'" -vsync vfr frame_%04d.jpg
```

### 2. 추출 간격 자동 계산

| 영상 길이 | Gemini (200장 권장) |
|----------|-------------------|
| 5분 | 모든 I-Frame |
| 15분 | 5초 간격 |
| 30분 | 10초 간격 |

### 3. AI 분석

```bash
# Gemini CLI
gemini "영상 프레임 분석 프롬프트 @frame_0001.jpg @frame_0002.jpg ..." -y

# 특정 모델 지정
gemini --model gemini-2.5-pro "프롬프트 @frame_0001.jpg ..." -y
```

## 🔧 개발

### 개발 환경 설정

```bash
# 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 개발 의존성 설치
pip install -e ".[dev]"

# 린트
ruff check src/

# 타입 체크
mypy src/
```

### 빌드

```bash
# PyInstaller로 실행 파일 생성
pip install -e ".[build]"
pyinstaller --onefile --windowed src/main.py
```

## 📝 라이선스

MIT License

## 🙏 감사

- [FFmpeg](https://ffmpeg.org/) - 영상 처리
- [PySide6](https://www.qt.io/qt-for-python) - GUI 프레임워크
- [Gemini CLI](https://github.com/google-gemini/gemini-cli) - AI 분석
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - YouTube 다운로드
