#!/bin/bash

# ============================================================================
#  Movie File Analyzer - 실행 스크립트
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
CONFIG_FILE="$HOME/.movie_file_analyzer/env_config"

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

    if ! check_command ffmpeg; then
        missing+=("ffmpeg")
    fi

    if [ ${#missing[@]} -ne 0 ]; then
        log_error "다음 의존성이 설치되어 있지 않습니다: ${missing[*]}"
        echo ""
        echo "설치 방법:"
        echo "  brew install ${missing[*]}"
        exit 1
    fi

    # AI CLI 확인
    local ai_available=()
    if check_command claude; then
        ai_available+=("claude")
    fi
    if check_command gemini; then
        ai_available+=("gemini")
    fi

    if [ ${#ai_available[@]} -eq 0 ]; then
        log_warn "AI CLI 도구가 설치되어 있지 않습니다."
        echo "  분석 기능을 사용하려면 claude 또는 gemini CLI를 설치하세요."
    else
        log_success "사용 가능한 AI: ${ai_available[*]}"
    fi
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

export MFA_DEFAULT_PROVIDER="${MFA_DEFAULT_PROVIDER:-claude}"
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

    # 1. AI 제공자 선택
    echo -e "${YELLOW}1. 기본 AI 제공자 선택:${NC}"
    local providers=()
    if check_command claude; then
        providers+=("claude (Anthropic Claude)")
    fi
    if check_command gemini; then
        providers+=("gemini (Google Gemini)")
    fi

    if [ ${#providers[@]} -gt 0 ]; then
        local selected_provider
        selected_provider=$(printf '%s\n' "${providers[@]}" | fzf --height=10 --prompt="AI 제공자 > " --header="↑↓로 선택, Enter로 확정")
        if [ -n "$selected_provider" ]; then
            MFA_DEFAULT_PROVIDER=$(echo "$selected_provider" | cut -d' ' -f1)
            log_success "선택됨: $MFA_DEFAULT_PROVIDER"
        fi
    else
        log_warn "설치된 AI CLI가 없습니다."
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
    echo -e "  AI 제공자: ${GREEN}${MFA_DEFAULT_PROVIDER:-claude}${NC}"
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
            "🚀 앱 실행" \
            "⚙️  환경 설정" \
            "📊 현재 설정 보기" \
            "🗑️  캐시 정리" \
            "❌ 종료" \
            | fzf --height=15 --prompt="선택 > " --header="Movie File Analyzer 메뉴")

        case "$choice" in
            "🚀 앱 실행")
                run_app
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
        --clean)
            cleanup_cache
            ;;
        --help|-h)
            echo "사용법: $0 [옵션]"
            echo ""
            echo "옵션:"
            echo "  --config, -c    환경 설정 (fzf 필요)"
            echo "  --run, -r       바로 앱 실행"
            echo "  --clean         캐시 정리"
            echo "  --help, -h      도움말"
            echo ""
            echo "옵션 없이 실행하면 메뉴가 표시됩니다 (fzf 필요)"
            ;;
        *)
            show_menu
            ;;
    esac
}

main "$@"
