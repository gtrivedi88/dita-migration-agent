#!/bin/bash
# setup.sh — Install prerequisites and configure your AsciiDoc project for DITA migration
#
# Usage:
#   ./setup.sh <path-to-your-asciidoc-project>
#
# Example:
#   ./setup.sh ../devspaces-dita-migration
#   ./setup.sh ../my-docs-repo
#
# What this script does:
#   1. Checks that vale is installed (installs if missing)
#   2. Configures .vale.ini in your project to use the styles from this repo
#   3. Verifies the setup works by running vale on a test file

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STYLES_DIR="$SCRIPT_DIR/styles"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# --- Check arguments ---
if [ $# -lt 1 ]; then
    error "Usage: ./setup.sh <path-to-your-asciidoc-project>"
    echo ""
    echo "Example:"
    echo "  ./setup.sh ../devspaces-dita-migration"
    echo "  ./setup.sh ../my-docs-repo"
    exit 1
fi

PROJECT_DIR="$(cd "$1" 2>/dev/null && pwd)" || {
    error "Directory not found: $1"
    exit 1
}

echo ""
echo "============================================================"
echo "  DITA Migration Agent — Setup"
echo "============================================================"
echo ""
echo "  Agent repo:   $SCRIPT_DIR"
echo "  Target project: $PROJECT_DIR"
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
    echo "  macOS:   brew install vale"
    echo "  Linux:   snap install vale"
    echo "  Manual:  https://vale.sh/docs/install/"
    echo ""

    read -p "Would you like to try automatic installation? [y/N] " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if command -v brew &>/dev/null; then
            info "Installing vale via brew..."
            brew install vale
        elif command -v snap &>/dev/null; then
            info "Installing vale via snap..."
            sudo snap install vale
        else
            error "No supported package manager found (brew or snap)."
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

# --- Step 3: Configure .vale.ini in the target project ---
info "Configuring .vale.ini in $PROJECT_DIR..."

# Calculate relative path from project to styles
RELATIVE_STYLES=$(python3 -c "import os.path; print(os.path.relpath('$STYLES_DIR', '$PROJECT_DIR'))")

VALE_INI="$PROJECT_DIR/.vale.ini"

if [ -f "$VALE_INI" ]; then
    warn ".vale.ini already exists at $VALE_INI"
    echo "  Current StylesPath: $(grep -E '^StylesPath' "$VALE_INI" 2>/dev/null || echo '(not set)')"
    echo ""
    read -p "Overwrite with new configuration? [y/N] " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        info "Keeping existing .vale.ini"
    else
        # Backup existing
        cp "$VALE_INI" "$VALE_INI.bak"
        info "Backed up existing .vale.ini to .vale.ini.bak"
    fi
fi

# Write .vale.ini if user agreed or it doesn't exist
if [ ! -f "$VALE_INI" ] || [[ ${REPLY:-} =~ ^[Yy]$ ]]; then
    cat > "$VALE_INI" << EOF
StylesPath = $RELATIVE_STYLES
MinAlertLevel = warning

[*.adoc]
BasedOnStyles = AsciiDocDITA, RedHat

# Exclude snippet files — they are include fragments, not standalone modules
[**/snippets/*.adoc]
BasedOnStyles =

[**/common/*.adoc]
BasedOnStyles =

[snippets/*.adoc]
BasedOnStyles =

[common/*.adoc]
BasedOnStyles =
EOF
    info "Created .vale.ini with StylesPath = $RELATIVE_STYLES"
fi

# --- Step 4: Verify ---
info "Verifying setup..."

# Find a .adoc file to test
TEST_FILE=$(find "$PROJECT_DIR" -name "*.adoc" -not -path "*/snippets/*" -not -path "*/common/*" | head -1)

if [ -n "$TEST_FILE" ]; then
    if cd "$PROJECT_DIR" && vale --output=JSON "$TEST_FILE" &>/dev/null; then
        ISSUE_COUNT=$(cd "$PROJECT_DIR" && vale --output=JSON "$TEST_FILE" 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
total = sum(len(v) for v in data.values())
print(total)
" 2>/dev/null || echo "?")
        info "Vale runs successfully. Found $ISSUE_COUNT issues in test file."
    else
        warn "Vale returned an error on the test file. Check your .vale.ini configuration."
    fi
else
    warn "No .adoc files found in $PROJECT_DIR. Setup complete but could not verify."
fi

# --- Done ---
echo ""
echo "============================================================"
echo "  Setup complete"
echo "============================================================"
echo ""
echo "  Next steps:"
echo ""
echo "  1. Open Claude Code from this directory:"
echo "     cd $(basename "$SCRIPT_DIR") && claude"
echo ""
echo "  2. Run a check on your project:"
echo "     /vale-check $1/"
echo ""
echo "  3. Fix violations (recommended: one assembly at a time):"
echo "     /vale-fix $1/assemblies/assembly_getting-started.adoc"
echo ""
echo "============================================================"
