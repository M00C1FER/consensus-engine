#!/usr/bin/env bash
# Consensus Engine — install wizard
# Supports: Linux, WSL, Termux (Android)
set -euo pipefail

BLUE='\033[0;34m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERR]${NC}   $*"; exit 1; }
prompt()  { echo -e "${YELLOW}[INPUT]${NC} $*"; }

detect_platform() {
    if [ -n "${TERMUX_VERSION:-}" ] || [ -d "/data/data/com.termux" ]; then echo "termux"
    elif grep -qi microsoft /proc/version 2>/dev/null; then echo "wsl"
    else echo "linux"; fi
}

install_deps_system() {
    local plat="$1"
    case "$plat" in
        termux) pkg update -y; pkg install -y python git ;;
        wsl|linux)
            if command -v apt-get &>/dev/null; then
                sudo apt-get update -qq
                sudo apt-get install -y python3 python3-venv python3-pip git
            elif command -v dnf &>/dev/null; then
                sudo dnf install -y python3 python3-virtualenv git
            elif command -v pacman &>/dev/null; then
                sudo pacman -Sy --noconfirm python git
            elif command -v apk &>/dev/null; then
                sudo apk add --no-cache python3 py3-pip git
            fi ;;
    esac
}

PLATFORM=$(detect_platform)
INSTALL_DIR="${HOME}/.local/share/consensus-engine"
VENV_DIR="${INSTALL_DIR}/.venv"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║       Consensus Engine  v1.0.0           ║"
echo "║  Delphi-style multi-agent convergence    ║"
echo "╚══════════════════════════════════════════╝"
echo ""
info "Platform: $PLATFORM"

install_deps_system "$PLATFORM"
mkdir -p "$INSTALL_DIR"
if [ "$PLATFORM" = "termux" ]; then python -m venv "$VENV_DIR"
else python3 -m venv "$VENV_DIR"; fi
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install . -q

ENV_FILE="${INSTALL_DIR}/.env"
touch "$ENV_FILE"; chmod 600 "$ENV_FILE"

echo ""
echo "────────────────────────────────────────────"
echo " Configuration (all fields optional)"
echo "────────────────────────────────────────────"

prompt "Min consensus threshold, 0.0–1.0 (default: 0.6):"
read -r threshold
if [ -n "$threshold" ]; then echo "CONSENSUS_MIN_THRESHOLD=${threshold}" >> "$ENV_FILE"; fi

prompt "Max Delphi rounds (default: 5):"
read -r rounds
if [ -n "$rounds" ]; then echo "CONSENSUS_MAX_ROUNDS=${rounds}" >> "$ENV_FILE"; fi

prompt "Consensus home directory (default: $INSTALL_DIR):"
read -r home_path
if [ -n "$home_path" ]; then echo "CONSENSUS_HOME=${home_path}" >> "$ENV_FILE"; fi

success "Config saved to $ENV_FILE"

WRAPPER="${HOME}/.local/bin/consensus"
mkdir -p "$(dirname "$WRAPPER")"
cat > "$WRAPPER" << WRAPEOF
#!/usr/bin/env bash
set -a; [ -f "${ENV_FILE}" ] && . "${ENV_FILE}"; set +a
exec "${VENV_DIR}/bin/consensus" "\$@"
WRAPEOF
chmod +x "$WRAPPER"

echo ""
success "Installation complete!"
echo ""
echo "  Usage:  consensus --help"
echo "  Docs:   https://github.com/M00C1FER/consensus-engine"
