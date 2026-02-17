#!/bin/bash
# setup.sh — Verify prerequisites for the DITA Migration Agent
#
# Usage:
#   ./setup.sh
#
# What this script does:
#   1. Checks that vale is installed (installs if missing)
#   2. Verifies the agent's styles exist
#   3. Verifies the agent's .vale.ini is valid

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STYLES_DIR="$SCRIPT_DIR/styles"
VALE_INI="$SCRIPT_DIR/.vale.ini"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
echo "============================================================"
echo "  DITA Migration Agent — Setup"
echo "============================================================"
echo ""
echo "  Agent repo: $SCRIPT_DIR"
echo ""

# --- Step 1: Check vale ---
info "Checking for vale..."

if command -v vale &>/dev/null; then
    VALE_VERSION=$(vale --version 2>&1 | head -1)
    info "vale is installed: $VALE_VERSION"
else
    warn "vale is not installed."
    echo ""
    echo "Install vale using one of these methods:"
    echo ""
    echo "  macOS:       brew install vale"
    echo "  Fedora/RHEL: sudo dnf install vale"
    echo "  Ubuntu:      sudo snap install vale"
    echo "  Manual:      https://vale.sh/docs/install/"
    echo ""

    read -p "Would you like to try automatic installation? [y/N] " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command -v brew &>/dev/null; then
            info "Installing vale via brew..."
            brew install vale
        elif command -v dnf &>/dev/null; then
            info "Installing vale via dnf..."
            sudo dnf install -y vale
        elif command -v snap &>/dev/null; then
            info "Installing vale via snap..."
            sudo snap install vale
        else
            error "No supported package manager found (brew, dnf, or snap)."
            echo "Please install vale manually: https://vale.sh/docs/install/"
            exit 1
        fi

        if command -v vale &>/dev/null; then
            info "vale installed successfully: $(vale --version 2>&1 | head -1)"
        else
            error "vale installation failed. Please install manually."
            exit 1
        fi
    else
        error "vale is required. Please install it and re-run this script."
        exit 1
    fi
fi

# --- Step 2: Verify styles exist ---
info "Checking styles..."

if [ ! -d "$STYLES_DIR/AsciiDocDITA" ]; then
    error "AsciiDocDITA styles not found at $STYLES_DIR/AsciiDocDITA"
    exit 1
fi

if [ ! -d "$STYLES_DIR/RedHat" ]; then
    error "RedHat styles not found at $STYLES_DIR/RedHat"
    exit 1
fi

DITA_COUNT=$(ls "$STYLES_DIR/AsciiDocDITA/"*.yml 2>/dev/null | wc -l)
REDHAT_COUNT=$(ls "$STYLES_DIR/RedHat/"*.yml 2>/dev/null | wc -l)
info "Found $DITA_COUNT AsciiDocDITA rules and $REDHAT_COUNT RedHat rules"

# --- Step 3: Verify .vale.ini ---
info "Checking agent .vale.ini..."

if [ ! -f "$VALE_INI" ]; then
    error ".vale.ini not found at $VALE_INI"
    error "The agent repo may be incomplete. Try re-cloning."
    exit 1
fi

info ".vale.ini found at $VALE_INI"

# Verify vale can load the config
if vale ls-config --config="$VALE_INI" &>/dev/null; then
    info "Vale config is valid."
else
    warn "Vale could not load $VALE_INI. Check the config syntax."
fi

# --- Done ---
echo ""
echo "============================================================"
echo "  Setup complete — agent is ready"
echo "============================================================"
echo ""
echo "  Next steps:"
echo ""
echo "  1. Open Claude Code from this directory:"
echo "     cd $SCRIPT_DIR && claude"
echo ""
echo "  2. Run a check on your project:"
echo "     /vale-check ../your-project/topics/"
echo ""
echo "  3. Fix violations (recommended: one assembly at a time):"
echo "     /vale-fix ../your-project/assemblies/assembly_getting-started.adoc"
echo ""
echo "============================================================"
