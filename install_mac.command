#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✓${NC} $1"; }
info() { echo -e "${YELLOW}→${NC} $1"; }
fail() { echo -e "${RED}✗ $1${NC}"; exit 1; }

echo ""
echo "Supernote OCR — installer"
echo "========================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Homebrew ──────────────────────────────────────────────────────────────────
if ! command -v brew &>/dev/null; then
    fail "Homebrew is not installed. Install it from https://brew.sh and re-run this script."
fi
ok "Homebrew found"

# ── Ollama ────────────────────────────────────────────────────────────────────
if ! command -v ollama &>/dev/null; then
    info "Installing Ollama..."
    brew install --cask ollama
fi
ok "Ollama found"

# ── micromamba ────────────────────────────────────────────────────────────────
if ! command -v micromamba &>/dev/null; then
    info "Installing micromamba..."
    brew install micromamba
fi
ok "micromamba found"

# ── Python environment ────────────────────────────────────────────────────────
if ! micromamba env list | grep -q "^supernote-ocr "; then
    info "Creating Python environment..."
    micromamba create -y -n supernote-ocr -c conda-forge python=3.12 pip
fi
ok "Python environment ready"

# ── poppler ───────────────────────────────────────────────────────────────────
if ! micromamba run -n supernote-ocr pdftoppm --version &>/dev/null 2>&1; then
    info "Installing poppler..."
    micromamba install -y -n supernote-ocr -c conda-forge poppler
fi
ok "poppler found"

# ── Python dependencies ───────────────────────────────────────────────────────
info "Installing Python dependencies..."
micromamba run -n supernote-ocr python -m pip install -q -r "$SCRIPT_DIR/requirements_native.txt"
ok "Python dependencies installed"

# ── Ollama model ──────────────────────────────────────────────────────────────
if ollama list 2>/dev/null | grep -q "qwen3-vl:8b-instruct"; then
    ok "Model qwen3-vl:8b-instruct already downloaded"
else
    info "Downloading qwen3-vl:8b-instruct (~5 GB, this may take a while)..."
    ollama pull qwen3-vl:8b-instruct
    ok "Model downloaded"
fi

# ── Launcher permissions ──────────────────────────────────────────────────────
chmod +x "$SCRIPT_DIR/launch_ocr_gui_mac.command"
ok "launch_ocr_gui_mac.command made executable"

echo ""
echo -e "${GREEN}All done!${NC}"
echo ""
echo "To launch the GUI:  double-click launch_ocr_gui_mac.command in Finder"
echo "  (first time: right-click → Open to pass macOS Gatekeeper)"
echo "To use the CLI:     micromamba run -n supernote-ocr python native_qwen_ocr.py --help"
echo ""
