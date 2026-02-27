#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════
#  🎬 Video Downloader & Converter - 로컬 WebUI
#  720p 다운로드 → 1080p 업스케일 → HandBrake 코덱 변환
#  macOS / Linux 원클릭 설치 & 실행 스크립트
# ═══════════════════════════════════════════════════════

set -e

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

print_header() {
    echo ""
    echo -e "${PURPLE}══════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}  🎬 Video Downloader & Converter - 로컬 WebUI${NC}"
    echo -e "${CYAN}  720p 다운로드 → 1080p 업스케일 → HandBrake 코덱 변환${NC}"
    echo -e "${PURPLE}══════════════════════════════════════════════════════${NC}"
    echo ""
}

print_step() {
    echo -e "${YELLOW}──── $1 ────${NC}"
}

print_ok() {
    echo -e "${GREEN}[✓] $1${NC}"
}

print_warn() {
    echo -e "${YELLOW}[!] $1${NC}"
}

print_err() {
    echo -e "${RED}[✗] $1${NC}"
}

# ─── 작업 디렉토리 ───
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

print_header

# ─── OS 감지 ───
OS="unknown"
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="mac"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
fi
echo -e "${BLUE}[*] 운영체제: ${OS} (${OSTYPE})${NC}"
echo ""

# ═══════════════════════════════════════
# STEP 1: 패키지 관리자 확인
# ═══════════════════════════════════════
print_step "STEP 1/6: 패키지 관리자 확인"

if [[ "$OS" == "mac" ]]; then
    if ! command -v brew &>/dev/null; then
        print_warn "Homebrew가 설치되어 있지 않습니다. 설치합니다..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        # Apple Silicon 경로
        if [[ -f "/opt/homebrew/bin/brew" ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
    fi
    print_ok "Homebrew 감지됨"
    PKG_INSTALL="brew install"
    PKG_UPDATE="brew update"
elif [[ "$OS" == "linux" ]]; then
    if command -v apt-get &>/dev/null; then
        PKG_INSTALL="sudo apt-get install -y"
        PKG_UPDATE="sudo apt-get update"
    elif command -v dnf &>/dev/null; then
        PKG_INSTALL="sudo dnf install -y"
        PKG_UPDATE="sudo dnf check-update || true"
    elif command -v pacman &>/dev/null; then
        PKG_INSTALL="sudo pacman -S --noconfirm"
        PKG_UPDATE="sudo pacman -Sy"
    else
        print_err "지원하지 않는 패키지 관리자입니다."
        exit 1
    fi
    print_ok "패키지 관리자 감지됨"
fi
echo ""

# ═══════════════════════════════════════
# STEP 2: Python 확인 / 설치
# ═══════════════════════════════════════
print_step "STEP 2/6: Python 확인"

PYTHON_CMD=""
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
fi

if [[ -z "$PYTHON_CMD" ]]; then
    print_warn "Python이 설치되어 있지 않습니다. 설치합니다..."
    $PKG_UPDATE
    if [[ "$OS" == "mac" ]]; then
        brew install python@3.11
    else
        $PKG_INSTALL python3 python3-pip python3-venv
    fi
    PYTHON_CMD="python3"
fi

PYTHON_VER=$($PYTHON_CMD --version 2>&1)
print_ok "$PYTHON_VER 감지됨"
echo ""

# ═══════════════════════════════════════
# STEP 3: FFmpeg 확인 / 설치
# ═══════════════════════════════════════
print_step "STEP 3/6: FFmpeg 확인"

if ! command -v ffmpeg &>/dev/null; then
    print_warn "FFmpeg이 설치되어 있지 않습니다. 설치합니다..."
    if [[ "$OS" == "mac" ]]; then
        brew install ffmpeg
    else
        $PKG_INSTALL ffmpeg
    fi
fi

if command -v ffmpeg &>/dev/null; then
    print_ok "FFmpeg 감지됨"
else
    print_err "FFmpeg 설치 실패. 수동으로 설치해주세요."
fi
echo ""

# ═══════════════════════════════════════
# STEP 4: HandBrakeCLI 확인 / 설치
# ═══════════════════════════════════════
print_step "STEP 4/6: HandBrakeCLI 확인"

if ! command -v HandBrakeCLI &>/dev/null; then
    print_warn "HandBrakeCLI가 설치되어 있지 않습니다. 설치합니다..."
    if [[ "$OS" == "mac" ]]; then
        brew install --cask handbrake
        # CLI도 별도 설치
        brew install handbrake
    else
        # Ubuntu/Debian
        if command -v apt-get &>/dev/null; then
            sudo add-apt-repository -y ppa:stebbins/handbrake-releases 2>/dev/null || true
            sudo apt-get update
            sudo apt-get install -y handbrake-cli
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y handbrake-cli
        elif command -v pacman &>/dev/null; then
            sudo pacman -S --noconfirm handbrake-cli
        fi
    fi
fi

if command -v HandBrakeCLI &>/dev/null; then
    print_ok "HandBrakeCLI 감지됨"
else
    print_err "HandBrakeCLI 설치 실패. 수동으로 설치해주세요."
    echo "  macOS:  brew install handbrake"
    echo "  Linux:  sudo apt install handbrake-cli"
fi
echo ""

# ═══════════════════════════════════════
# STEP 5: Python 가상환경 + 패키지
# ═══════════════════════════════════════
print_step "STEP 5/6: Python 환경 설정"

if [[ ! -d "venv" ]]; then
    echo "[*] 가상환경 생성 중..."
    $PYTHON_CMD -m venv venv
fi

# 가상환경 활성화
source venv/bin/activate

echo "[*] Python 패키지 설치 중..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
print_ok "패키지 설치 완료!"
echo ""

# ═══════════════════════════════════════
# 폴더 생성
# ═══════════════════════════════════════
mkdir -p downloads converted final templates

# ═══════════════════════════════════════
# STEP 6: 서버 실행
# ═══════════════════════════════════════
print_step "STEP 6/6: WebUI 서버 시작"
echo ""
echo -e "${PURPLE}══════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${GREEN}  🌐 WebUI 주소: http://localhost:5000${NC}"
echo -e "${CYAN}  종료하려면 Ctrl+C 를 누르세요${NC}"
echo -e "${PURPLE}══════════════════════════════════════════════════════${NC}"
echo ""

# 2초 후 브라우저 자동 열기
(sleep 2 && {
    if [[ "$OS" == "mac" ]]; then
        open "http://localhost:5000"
    else
        xdg-open "http://localhost:5000" 2>/dev/null || \
        sensible-browser "http://localhost:5000" 2>/dev/null || \
        echo -e "${YELLOW}[!] 브라우저를 수동으로 열어주세요: http://localhost:5000${NC}"
    fi
}) &

# Flask 서버 실행
$PYTHON_CMD app.py
