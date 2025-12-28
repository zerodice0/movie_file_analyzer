#!/bin/bash

# ============================================================================
#  Movie File Analyzer - 실행 스크립트
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
CONFIG_FILE="$HOME/.movie_file_analyzer/env_config"
SKILL_SOURCE_DIR="$SCRIPT_DIR/claude-code-skill"
SKILL_TARGET_DIR="$HOME/.claude/skills/movie-file-analyzer"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ============================================================================
# ASCII 아트 배너
# ============================================================================
show_banner() {
    echo -e "${CYAN}"
    cat << 'EOF'
    __  ___           _         _______ __        ___                __
   /  |/  /___ _   __(_)__     / ____(_) /__     /   |  ____  ____ _/ /_  ______  ___  _____
  / /|_/ / __ \ | / / / _ \   / /_  / / / _ \   / /| | / __ \/ __ `/ / / / /_  / / _ \/ ___/
 / /  / / /_/ / |/ / /  __/  / __/ / / /  __/  / ___ |/ / / / /_/ / / /_/ / / /_/  __/ /
/_/  /_/\____/|___/_/\___/  /_/   /_/_/\___/  /_/  |_/_/ /_/\__,_/_/\__, / /___/\___/_/
                                                                   /____/
EOF
    echo -e "${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  📹 영상에서 I-Frame을 추출하고 AI로 내용을 텍스트화하는 도구${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# ============================================================================
# 유틸리티 함수
# ============================================================================
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# ============================================================================
# 의존성 확인
# ============================================================================
check_dependencies() {
    local missing=()

    if ! check_command python3; then
        missing+=("python3")
    fi

    if [ ${#missing[@]} -ne 0 ]; then
        log_error "다음 의존성이 설치되어 있지 않습니다: ${missing[*]}"
        echo ""
        echo "설치 방법:"
        echo "  brew install ${missing[*]}"
        exit 1
    fi

    # 필수/선택 의존성 상태 표시
    local status_ffmpeg="❌"
    local status_gemini="❌"
    local status_ytdlp="❌"

    check_command ffmpeg && status_ffmpeg="✅"
    check_command gemini && status_gemini="✅"
    (check_command yt-dlp || check_command yt_dlp) && status_ytdlp="✅"

    # 필수 의존성 확인
    if ! check_command ffmpeg; then
        log_warn "ffmpeg가 설치되어 있지 않습니다. (필수)"
        echo "  설치: brew install ffmpeg 또는 📦 의존성 관리 메뉴 이용"
    fi

    # Gemini CLI 확인
    if ! check_command gemini; then
        log_warn "gemini CLI가 설치되어 있지 않습니다. (AI 분석에 필수)"
        echo "  설치: npm install -g @google/gemini-cli 또는 📦 의존성 관리 메뉴 이용"
    else
        log_success "Gemini CLI 사용 가능"
    fi
}

# ============================================================================
# 의존성 상태 확인
# ============================================================================
show_dependency_status() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  📦 의존성 상태${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # Python
    if check_command python3; then
        local py_version
        py_version=$(python3 --version 2>&1)
        echo -e "  ✅ ${GREEN}python3${NC} - $py_version"
    else
        echo -e "  ❌ ${RED}python3${NC} - 미설치 (필수)"
    fi

    # FFmpeg
    if check_command ffmpeg; then
        local ff_version
        ff_version=$(ffmpeg -version 2>&1 | head -1 | sed 's/ffmpeg version //' | cut -d' ' -f1)
        echo -e "  ✅ ${GREEN}ffmpeg${NC} - v$ff_version (프레임 추출용, 필수)"
    else
        echo -e "  ❌ ${RED}ffmpeg${NC} - 미설치 (프레임 추출용, 필수)"
    fi

    # Gemini CLI
    if check_command gemini; then
        local gemini_version
        gemini_version=$(gemini --version 2>&1 || echo "unknown")
        echo -e "  ✅ ${GREEN}gemini${NC} - v$gemini_version (AI 분석용, 필수)"
    else
        echo -e "  ❌ ${RED}gemini${NC} - 미설치 (AI 분석용, 필수)"
    fi

    # yt-dlp
    if check_command yt-dlp; then
        local ytdlp_version
        ytdlp_version=$(yt-dlp --version 2>&1)
        echo -e "  ✅ ${GREEN}yt-dlp${NC} - v$ytdlp_version (YouTube 다운로드용, 선택)"
    elif check_command yt_dlp; then
        echo -e "  ✅ ${GREEN}yt-dlp${NC} - 설치됨 (YouTube 다운로드용, 선택)"
    else
        echo -e "  ⚪ ${YELLOW}yt-dlp${NC} - 미설치 (YouTube 다운로드용, 선택)"
    fi

    # Node.js (gemini-cli 설치에 필요)
    if check_command node; then
        local node_version
        node_version=$(node --version 2>&1)
        echo -e "  ✅ ${GREEN}node${NC} - $node_version (gemini-cli 설치에 필요)"
    else
        echo -e "  ⚪ ${YELLOW}node${NC} - 미설치 (gemini-cli 설치에 필요)"
    fi

    # npm
    if check_command npm; then
        local npm_version
        npm_version=$(npm --version 2>&1)
        echo -e "  ✅ ${GREEN}npm${NC} - v$npm_version"
    else
        echo -e "  ⚪ ${YELLOW}npm${NC} - 미설치"
    fi

    echo ""
}

# ============================================================================
# 의존성 설치 함수들
# ============================================================================
install_ffmpeg() {
    echo ""
    log_info "ffmpeg 설치 중..."

    if check_command brew; then
        brew install ffmpeg
        log_success "ffmpeg 설치 완료"
    else
        log_error "Homebrew가 설치되어 있지 않습니다."
        echo "  먼저 Homebrew를 설치하세요: https://brew.sh"
        echo "  또는 수동으로 ffmpeg를 설치하세요: https://ffmpeg.org/download.html"
    fi
    echo ""
}

install_ytdlp() {
    echo ""
    log_info "yt-dlp 설치 중..."

    # pip로 설치 시도
    if check_command pip3; then
        pip3 install --user yt-dlp
        log_success "yt-dlp 설치 완료 (pip)"
    elif check_command pip; then
        pip install --user yt-dlp
        log_success "yt-dlp 설치 완료 (pip)"
    elif check_command brew; then
        brew install yt-dlp
        log_success "yt-dlp 설치 완료 (brew)"
    else
        # 직접 다운로드
        log_info "pip/brew가 없어 직접 다운로드합니다..."
        mkdir -p "$HOME/bin"
        curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o "$HOME/bin/yt-dlp"
        chmod +x "$HOME/bin/yt-dlp"

        # PATH에 ~/bin 추가 안내
        if [[ ":$PATH:" != *":$HOME/bin:"* ]]; then
            log_warn "~/bin이 PATH에 없습니다. 다음을 ~/.zshrc 또는 ~/.bashrc에 추가하세요:"
            echo "  export PATH=\"\$HOME/bin:\$PATH\""
        fi
        log_success "yt-dlp 설치 완료 ($HOME/bin/yt-dlp)"
    fi
    echo ""
}

install_gemini_cli() {
    echo ""
    log_info "gemini-cli 설치 중..."

    if ! check_command npm; then
        log_error "npm이 설치되어 있지 않습니다."
        echo "  먼저 Node.js를 설치하세요:"
        echo "    brew install node"
        echo "  또는: https://nodejs.org/"
        echo ""
        return 1
    fi

    npm install -g @google/gemini-cli
    log_success "gemini-cli 설치 완료"
    echo ""
    log_info "gemini-cli 사용을 위해 Google 계정 인증이 필요합니다."
    echo "  처음 실행 시 'gemini' 명령어로 인증을 진행하세요."
    echo ""
}

install_all_dependencies() {
    echo ""
    log_info "누락된 모든 의존성을 설치합니다..."
    echo ""

    local installed=0

    if ! check_command ffmpeg; then
        install_ffmpeg
        ((installed++))
    fi

    if ! check_command gemini; then
        install_gemini_cli
        ((installed++))
    fi

    if ! check_command yt-dlp && ! check_command yt_dlp; then
        install_ytdlp
        ((installed++))
    fi

    if [ $installed -eq 0 ]; then
        log_success "모든 의존성이 이미 설치되어 있습니다!"
    else
        log_success "$installed개의 도구가 설치되었습니다."
    fi
    echo ""
}

# ============================================================================
# Claude Code 스킬 설치
# ============================================================================
install_claude_skill() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  🤖 Claude Code 스킬 설치${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # 스킬 소스 확인
    if [ ! -d "$SKILL_SOURCE_DIR" ]; then
        log_error "스킬 소스 디렉토리를 찾을 수 없습니다: $SKILL_SOURCE_DIR"
        return 1
    fi

    # 대상 디렉토리 생성
    mkdir -p "$HOME/.claude/skills"

    # 기존 스킬 확인
    if [ -d "$SKILL_TARGET_DIR" ]; then
        log_warn "기존 스킬이 발견되었습니다."
        read -p "덮어쓰시겠습니까? [y/N] " confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            log_info "스킬 설치를 취소합니다."
            return 0
        fi
        rm -rf "$SKILL_TARGET_DIR"
    fi

    # 스킬 복사
    cp -r "$SKILL_SOURCE_DIR" "$SKILL_TARGET_DIR"

    # SKILL.md의 경로를 실제 설치 경로로 업데이트
    if [ -f "$SKILL_TARGET_DIR/SKILL.md" ]; then
        # 경로를 현재 스크립트 디렉토리로 업데이트
        sed -i "s|/home/user/movie_file_analyzer|$SCRIPT_DIR|g" "$SKILL_TARGET_DIR/SKILL.md"
        sed -i "s|~/path/to/movie_file_analyzer|$SCRIPT_DIR|g" "$SKILL_TARGET_DIR/SKILL.md"
    fi

    log_success "Claude Code 스킬이 설치되었습니다!"
    echo ""
    echo -e "${YELLOW}설치 위치:${NC} $SKILL_TARGET_DIR"
    echo ""
    echo -e "${CYAN}사용법:${NC}"
    echo "  Claude Code에서 영상 분석을 요청하면 자동으로 이 스킬이 활성화됩니다."
    echo ""
    echo "  예시:"
    echo "    - '이 영상 분석해줘: /path/to/video.mp4'"
    echo "    - 'YouTube 영상 분석해줘: https://youtube.com/watch?v=...'"
    echo "    - '분석 히스토리 보여줘'"
    echo ""
}

uninstall_claude_skill() {
    echo ""
    log_info "Claude Code 스킬 제거 중..."

    if [ -d "$SKILL_TARGET_DIR" ]; then
        rm -rf "$SKILL_TARGET_DIR"
        log_success "Claude Code 스킬이 제거되었습니다."
    else
        log_info "설치된 스킬이 없습니다."
    fi
    echo ""
}

show_skill_status() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  🤖 Claude Code 스킬 상태${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    if [ -d "$SKILL_TARGET_DIR" ]; then
        echo -e "  ✅ ${GREEN}스킬 설치됨${NC}"
        echo -e "     위치: $SKILL_TARGET_DIR"
        if [ -f "$SKILL_TARGET_DIR/SKILL.md" ]; then
            local desc
            desc=$(grep "^description:" "$SKILL_TARGET_DIR/SKILL.md" 2>/dev/null | head -1 | cut -d':' -f2- | xargs)
            if [ -n "$desc" ]; then
                echo -e "     설명: ${desc:0:60}..."
            fi
        fi
    else
        echo -e "  ❌ ${RED}스킬 미설치${NC}"
        echo ""
        echo "  스킬을 설치하려면: ./run.sh --install-skill"
    fi
    echo ""
}

# ============================================================================
# 의존성 관리 메뉴
# ============================================================================
show_dependency_menu() {
    if ! check_command fzf; then
        log_warn "fzf가 설치되어 있지 않습니다."
        show_dependency_status
        return
    fi

    while true; do
        local choice
        choice=$(printf '%s\n' \
            "📋 상태 확인" \
            "🔧 ffmpeg 설치 (프레임 추출)" \
            "🔧 gemini-cli 설치 (AI 분석)" \
            "🔧 yt-dlp 설치 (YouTube 다운로드)" \
            "🔧 모두 설치 (누락된 항목)" \
            "🔙 돌아가기" \
            | fzf --height=15 --prompt="의존성 관리 > " --header="설치할 도구를 선택하세요")

        case "$choice" in
            "📋 상태 확인")
                show_dependency_status
                read -p "Enter를 눌러 계속..."
                ;;
            "🔧 ffmpeg 설치 (프레임 추출)")
                install_ffmpeg
                read -p "Enter를 눌러 계속..."
                ;;
            "🔧 gemini-cli 설치 (AI 분석)")
                install_gemini_cli
                read -p "Enter를 눌러 계속..."
                ;;
            "🔧 yt-dlp 설치 (YouTube 다운로드)")
                install_ytdlp
                read -p "Enter를 눌러 계속..."
                ;;
            "🔧 모두 설치 (누락된 항목)")
                install_all_dependencies
                read -p "Enter를 눌러 계속..."
                ;;
            "🔙 돌아가기"|"")
                return
                ;;
        esac
    done
}

# ============================================================================
# 가상환경 설정
# ============================================================================
setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        log_info "가상환경 생성 중..."
        python3 -m venv "$VENV_DIR"
        log_success "가상환경 생성 완료"
    fi

    log_info "가상환경 활성화..."
    source "$VENV_DIR/bin/activate"

    # 의존성 설치 확인
    if ! python -c "import PySide6" 2>/dev/null; then
        log_info "의존성 설치 중..."
        pip install -q -e "$SCRIPT_DIR"
        log_success "의존성 설치 완료"
    fi
}

# ============================================================================
# fzf 기반 환경 설정
# ============================================================================
load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        source "$CONFIG_FILE"
    fi
}

save_config() {
    mkdir -p "$(dirname "$CONFIG_FILE")"
    cat > "$CONFIG_FILE" << EOF
# Movie File Analyzer 환경 설정
# 생성일: $(date)

export MFA_DEFAULT_MODEL="${MFA_DEFAULT_MODEL:-auto}"
export MFA_AUTO_CLEANUP="${MFA_AUTO_CLEANUP:-true}"
export MFA_MAX_CACHE_MB="${MFA_MAX_CACHE_MB:-1024}"
export MFA_DEFAULT_INTERVAL="${MFA_DEFAULT_INTERVAL:-auto}"
EOF
    log_success "설정이 저장되었습니다: $CONFIG_FILE"
}

configure_with_fzf() {
    if ! check_command fzf; then
        log_warn "fzf가 설치되어 있지 않습니다. 기본 설정을 사용합니다."
        echo "  fzf 설치: brew install fzf"
        return
    fi

    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  ⚙️  환경 설정 (fzf로 선택)${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # 1. Gemini 모델 선택
    echo -e "${YELLOW}1. Gemini 모델 선택:${NC}"
    if check_command gemini; then
        local selected_model
        selected_model=$(printf '%s\n' \
            "auto (자동 선택, 권장)" \
            "gemini-2.5-pro (안정, 권장)" \
            "gemini-2.5-flash (빠름)" \
            "gemini-2.0-flash (경량)" \
            | fzf --height=10 --prompt="모델 > " --header="↑↓로 선택, Enter로 확정")
        if [ -n "$selected_model" ]; then
            MFA_DEFAULT_MODEL=$(echo "$selected_model" | cut -d' ' -f1)
            log_success "선택됨: $MFA_DEFAULT_MODEL"
        fi
    else
        log_warn "gemini CLI가 설치되어 있지 않습니다."
        echo "  📦 의존성 관리 메뉴에서 설치할 수 있습니다."
    fi

    # 2. 캐시 자동 정리
    echo ""
    echo -e "${YELLOW}2. 분석 후 캐시 자동 정리:${NC}"
    local cleanup_selected
    cleanup_selected=$(printf '%s\n' "true (분석 후 자동 삭제)" "false (캐시 유지)" | fzf --height=10 --prompt="자동 정리 > ")
    if [ -n "$cleanup_selected" ]; then
        MFA_AUTO_CLEANUP=$(echo "$cleanup_selected" | cut -d' ' -f1)
        log_success "선택됨: $MFA_AUTO_CLEANUP"
    fi

    # 3. 최대 캐시 크기
    echo ""
    echo -e "${YELLOW}3. 최대 캐시 크기:${NC}"
    local cache_selected
    cache_selected=$(printf '%s\n' "512 (512MB)" "1024 (1GB, 권장)" "2048 (2GB)" "4096 (4GB)" | fzf --height=10 --prompt="캐시 크기 > ")
    if [ -n "$cache_selected" ]; then
        MFA_MAX_CACHE_MB=$(echo "$cache_selected" | cut -d' ' -f1)
        log_success "선택됨: ${MFA_MAX_CACHE_MB}MB"
    fi

    # 4. 기본 추출 간격
    echo ""
    echo -e "${YELLOW}4. 기본 추출 간격:${NC}"
    local interval_selected
    interval_selected=$(printf '%s\n' "auto (자동 계산, 권장)" "2 (2초 간격 - 상세)" "5 (5초 간격 - 표준)" "10 (10초 간격 - 간략)" | fzf --height=10 --prompt="추출 간격 > ")
    if [ -n "$interval_selected" ]; then
        MFA_DEFAULT_INTERVAL=$(echo "$interval_selected" | cut -d' ' -f1)
        log_success "선택됨: $MFA_DEFAULT_INTERVAL"
    fi

    # 설정 저장
    save_config
    echo ""
}

show_current_config() {
    echo ""
    echo -e "${CYAN}현재 설정:${NC}"
    echo -e "  Gemini 모델: ${GREEN}${MFA_DEFAULT_MODEL:-auto}${NC}"
    echo -e "  자동 정리: ${GREEN}${MFA_AUTO_CLEANUP:-true}${NC}"
    echo -e "  캐시 크기: ${GREEN}${MFA_MAX_CACHE_MB:-1024}MB${NC}"
    echo -e "  추출 간격: ${GREEN}${MFA_DEFAULT_INTERVAL:-auto}${NC}"
    echo ""
}

# ============================================================================
# 메인 메뉴
# ============================================================================
show_menu() {
    if check_command fzf; then
        local choice
        choice=$(printf '%s\n' \
            "🚀 앱 실행 (GUI)" \
            "🤖 Claude Code 스킬 설치" \
            "⚙️  환경 설정" \
            "📊 현재 설정 보기" \
            "📦 의존성 관리" \
            "🗑️  캐시 정리" \
            "❌ 종료" \
            | fzf --height=15 --prompt="선택 > " --header="Movie File Analyzer 메뉴")

        case "$choice" in
            "🚀 앱 실행 (GUI)")
                run_app
                ;;
            "🤖 Claude Code 스킬 설치")
                install_claude_skill
                read -p "Enter를 눌러 계속..."
                show_menu
                ;;
            "⚙️  환경 설정")
                configure_with_fzf
                show_menu
                ;;
            "📊 현재 설정 보기")
                show_current_config
                read -p "Enter를 눌러 계속..."
                show_menu
                ;;
            "📦 의존성 관리")
                show_dependency_menu
                show_menu
                ;;
            "🗑️  캐시 정리")
                cleanup_cache
                show_menu
                ;;
            "❌ 종료")
                echo "👋 종료합니다."
                exit 0
                ;;
            *)
                run_app
                ;;
        esac
    else
        run_app
    fi
}

cleanup_cache() {
    local cache_dir="$HOME/.movie_file_analyzer/cache"
    if [ -d "$cache_dir" ]; then
        local size
        size=$(du -sh "$cache_dir" 2>/dev/null | cut -f1)
        echo ""
        read -p "캐시($size)를 삭제하시겠습니까? [y/N] " confirm
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            rm -rf "$cache_dir"
            log_success "캐시가 삭제되었습니다."
        fi
    else
        log_info "삭제할 캐시가 없습니다."
    fi
    echo ""
}

# ============================================================================
# 앱 실행
# ============================================================================
run_app() {
    echo ""
    log_info "앱을 시작합니다..."
    echo ""

    cd "$SCRIPT_DIR"
    python -m src.main
}

# ============================================================================
# 메인
# ============================================================================
main() {
    show_banner
    check_dependencies
    setup_venv
    load_config

    # 커맨드라인 인자 처리
    case "${1:-}" in
        --config|-c)
            configure_with_fzf
            ;;
        --run|-r)
            run_app
            ;;
        --cli)
            # CLI 모드로 실행
            shift
            cd "$SCRIPT_DIR"
            python -m src.cli "$@"
            ;;
        --clean)
            cleanup_cache
            ;;
        --status)
            show_dependency_status
            ;;
        --install)
            install_all_dependencies
            ;;
        --install-skill)
            install_claude_skill
            ;;
        --uninstall-skill)
            uninstall_claude_skill
            ;;
        --skill-status)
            show_skill_status
            ;;
        --help|-h)
            echo "사용법: $0 [옵션]"
            echo ""
            echo "옵션:"
            echo "  --config, -c       환경 설정 (fzf 필요)"
            echo "  --run, -r          바로 앱 실행 (GUI)"
            echo "  --cli [args]       CLI 모드로 실행 (인자 전달)"
            echo "  --clean            캐시 정리"
            echo "  --status           의존성 상태 확인"
            echo "  --install          누락된 의존성 설치"
            echo "  --install-skill    Claude Code 스킬 설치"
            echo "  --uninstall-skill  Claude Code 스킬 제거"
            echo "  --skill-status     Claude Code 스킬 상태 확인"
            echo "  --help, -h         도움말"
            echo ""
            echo "CLI 사용 예시:"
            echo "  $0 --cli analyze video.mp4"
            echo "  $0 --cli history"
            echo "  $0 --cli cache status"
            echo ""
            echo "옵션 없이 실행하면 메뉴가 표시됩니다 (fzf 필요)"
            ;;
        *)
            show_menu
            ;;
    esac
}

main "$@"
