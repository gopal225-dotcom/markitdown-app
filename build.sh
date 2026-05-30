#!/bin/bash
# ============================================================
#  Build MarkItDown.app (and MarkItDown.dmg) on macOS
#  Run once on your Mac:   bash build.sh
# ============================================================
set -e

APP_NAME="MarkItDown"
ENTRY="markitdown_app.py"

echo "==> [1/5] Creating clean build environment"
python3 -m venv build-venv
source build-venv/bin/activate
pip install --upgrade pip --quiet

echo "==> [2/5] Installing dependencies (this can take a few minutes)"
pip install --quiet \
    "markitdown[all]" \
    flask \
    pywebview \
    pyinstaller

echo "==> [3/5] Building the .app with PyInstaller"
pyinstaller \
    --name "$APP_NAME" \
    --windowed \
    --noconfirm \
    --clean \
    --collect-all markitdown \
    --collect-all markitdown_converters \
    --collect-all magika \
    --collect-all onnxruntime \
    --collect-data magika \
    --hidden-import webview.platforms.cocoa \
    "$ENTRY"

echo "==> [4/5] .app built at: dist/$APP_NAME.app"

echo "==> [5/5] Creating DMG"
if command -v create-dmg >/dev/null 2>&1; then
    create-dmg \
        --volname "$APP_NAME" \
        --window-size 520 320 \
        --icon-size 100 \
        --app-drop-link 360 150 \
        --icon "$APP_NAME.app" 150 150 \
        "$APP_NAME.dmg" "dist/$APP_NAME.app" || true
else
    # Fallback: simple DMG without the fancy drag-to-Applications layout
    rm -f "$APP_NAME.dmg"
    hdiutil create -volname "$APP_NAME" \
        -srcfolder "dist/$APP_NAME.app" \
        -ov -format UDZO "$APP_NAME.dmg"
fi

deactivate
echo ""
echo "============================================================"
echo "  DONE"
echo "  App :  dist/$APP_NAME.app   (double-click to run)"
echo "  DMG :  $APP_NAME.dmg        (share / install)"
echo "============================================================"
