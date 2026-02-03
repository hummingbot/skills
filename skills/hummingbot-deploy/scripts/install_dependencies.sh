#!/bin/bash
#
# Install dependencies for Hummingbot deployment
# Usage: ./install_dependencies.sh [--yes]
#
set -eu

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

msg_info() { echo -e "${CYAN}[INFO]${NC} $1"; }
msg_ok() { echo -e "${GREEN}[OK]${NC} $1"; }
msg_warn() { echo -e "${YELLOW}[WARN]${NC} $1" >&2; }
msg_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# Parse arguments
AUTO_YES=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -y|--yes) AUTO_YES=true; shift ;;
        -h|--help)
            echo "Usage: $0 [-y|--yes]"
            echo ""
            echo "Options:"
            echo "  -y, --yes   Auto-confirm installation prompts"
            echo "  -h          Show this help"
            exit 0
            ;;
        *) shift ;;
    esac
done

# Detect OS
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

msg_info "Detected: $OS ($ARCH)"

# Check what's missing
MISSING=()
command -v git >/dev/null 2>&1 || MISSING+=("git")
command -v docker >/dev/null 2>&1 || MISSING+=("docker")
command -v curl >/dev/null 2>&1 || MISSING+=("curl")
command -v make >/dev/null 2>&1 || MISSING+=("make")

# Check docker-compose
if ! (docker compose version >/dev/null 2>&1 || command -v docker-compose >/dev/null 2>&1); then
    MISSING+=("docker-compose")
fi

if [[ ${#MISSING[@]} -eq 0 ]]; then
    msg_ok "All dependencies are already installed!"
    exit 0
fi

msg_warn "Missing dependencies: ${MISSING[*]}"

# Confirm installation
if ! $AUTO_YES; then
    echo ""
    read -p "Install missing dependencies? (y/n): " -r CONFIRM < /dev/tty
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        msg_info "Installation cancelled."
        exit 0
    fi
fi

# macOS installation
if [[ "$OS" == "darwin" ]]; then
    msg_info "Installing on macOS..."

    # Check for Homebrew
    if ! command -v brew >/dev/null 2>&1; then
        msg_error "Homebrew is required for macOS installation."
        msg_info "Install it from: https://brew.sh"
        echo ""
        echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
        exit 1
    fi

    for dep in "${MISSING[@]}"; do
        case $dep in
            docker)
                msg_info "Installing Docker Desktop..."
                if [[ "$ARCH" == "arm64" ]]; then
                    brew install --cask docker
                else
                    brew install --cask docker
                fi
                msg_ok "Docker installed. Please start Docker Desktop manually."
                echo -e "  Run: ${CYAN}open -a Docker${NC}"
                ;;
            docker-compose)
                msg_info "Docker Compose is included with Docker Desktop."
                ;;
            git|curl|make)
                msg_info "Installing $dep..."
                brew install "$dep"
                msg_ok "$dep installed."
                ;;
        esac
    done

    msg_ok "macOS dependencies installed!"

    if [[ " ${MISSING[*]} " =~ " docker " ]]; then
        echo ""
        msg_warn "Please start Docker Desktop before continuing."
        echo -e "  Run: ${CYAN}open -a Docker${NC}"
    fi

    exit 0
fi

# Linux installation
if [[ "$OS" == "linux" ]]; then
    msg_info "Installing on Linux..."

    # Check for root/sudo
    if [[ $EUID -ne 0 ]]; then
        if ! command -v sudo >/dev/null 2>&1; then
            msg_error "Root privileges required. Please run as root or install sudo."
            exit 1
        fi
        SUDO_CMD="sudo"
    else
        SUDO_CMD=""
    fi

    # Detect package manager
    if command -v apt-get >/dev/null 2>&1; then
        PKG_MGR="apt"
        UPDATE_CMD="$SUDO_CMD apt-get update"
        INSTALL_CMD="$SUDO_CMD apt-get install -y"
    elif command -v dnf >/dev/null 2>&1; then
        PKG_MGR="dnf"
        UPDATE_CMD="$SUDO_CMD dnf check-update || true"
        INSTALL_CMD="$SUDO_CMD dnf install -y"
    elif command -v yum >/dev/null 2>&1; then
        PKG_MGR="yum"
        UPDATE_CMD="$SUDO_CMD yum check-update || true"
        INSTALL_CMD="$SUDO_CMD yum install -y"
    elif command -v pacman >/dev/null 2>&1; then
        PKG_MGR="pacman"
        UPDATE_CMD="$SUDO_CMD pacman -Sy"
        INSTALL_CMD="$SUDO_CMD pacman -S --noconfirm"
    elif command -v apk >/dev/null 2>&1; then
        PKG_MGR="apk"
        UPDATE_CMD="$SUDO_CMD apk update"
        INSTALL_CMD="$SUDO_CMD apk add"
    else
        msg_error "Could not detect package manager."
        msg_info "Please install manually: ${MISSING[*]}"
        exit 1
    fi

    msg_info "Using package manager: $PKG_MGR"

    # Update package lists
    msg_info "Updating package lists..."
    eval "$UPDATE_CMD" || msg_warn "Package update had warnings, continuing..."

    for dep in "${MISSING[@]}"; do
        case $dep in
            docker)
                msg_info "Installing Docker..."
                if command -v curl >/dev/null 2>&1; then
                    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
                    $SUDO_CMD sh /tmp/get-docker.sh
                    rm -f /tmp/get-docker.sh

                    # Add user to docker group
                    if [[ $EUID -ne 0 ]] && command -v usermod >/dev/null 2>&1; then
                        $SUDO_CMD usermod -aG docker "$USER" || true
                        msg_info "Added $USER to docker group. Log out and back in for this to take effect."
                    fi

                    # Start Docker
                    if command -v systemctl >/dev/null 2>&1; then
                        $SUDO_CMD systemctl start docker
                        $SUDO_CMD systemctl enable docker
                    fi
                else
                    msg_error "curl is required to install Docker. Install curl first."
                    exit 1
                fi
                msg_ok "Docker installed."
                ;;
            docker-compose)
                msg_info "Installing docker-compose..."
                if [[ "$PKG_MGR" == "apt" ]]; then
                    $INSTALL_CMD docker-compose-plugin || $INSTALL_CMD docker-compose || true
                else
                    $INSTALL_CMD docker-compose || true
                fi
                msg_ok "docker-compose installed."
                ;;
            git|curl|make)
                msg_info "Installing $dep..."
                $INSTALL_CMD "$dep"
                msg_ok "$dep installed."
                ;;
        esac
    done

    msg_ok "Linux dependencies installed!"

    # Verify Docker is running
    if [[ " ${MISSING[*]} " =~ " docker " ]]; then
        sleep 2
        if docker info >/dev/null 2>&1; then
            msg_ok "Docker daemon is running."
        else
            msg_warn "Docker installed but may need a system restart or re-login."
            echo -e "  Try: ${CYAN}sudo systemctl start docker${NC}"
        fi
    fi

    exit 0
fi

# Unsupported OS
msg_error "Unsupported operating system: $OS"
msg_info "Please install dependencies manually:"
for dep in "${MISSING[@]}"; do
    echo "  - $dep"
done
exit 1
