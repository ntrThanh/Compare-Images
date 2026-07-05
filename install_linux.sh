#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

find_project_dir() {
    local dir="$1"
    while [ "$dir" != "/" ]; do
        if [ -f "$dir/main.py" ] && [ -d "$dir/assets" ]; then
            echo "$dir"
            return 0
        fi
        dir="$(dirname "$dir")"
    done
    return 1
}

PROJECT_DIR="$(find_project_dir "$SCRIPT_DIR" || true)"
if [ -z "${PROJECT_DIR:-}" ]; then
    echo "Error: Could not find project root (must contain main.py and assets/)."
    exit 1
fi

BINARY="$PROJECT_DIR/dist/ImageCompare/ImageCompare"
ICON_SRC="$PROJECT_DIR/assets/icon_256.png"

if [ ! -x "$BINARY" ]; then
    echo "Error: Binary not found at $BINARY"
    echo "Build first: pyinstaller build_app.spec"
    exit 1
fi

if [ ! -f "$ICON_SRC" ]; then
    echo "Error: Icon not found at $ICON_SRC"
    exit 1
fi

ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
mkdir -p "$ICON_DIR"
cp "$ICON_SRC" "$ICON_DIR/imagecompare.png"

APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPS_DIR"
DESKTOP_FILE="$APPS_DIR/imagecompare.desktop"

cat > "$DESKTOP_FILE" <<DESKTOP_EOF
[Desktop Entry]
Type=Application
Name=Image Compare
Comment=Visually compare multiple images side by side
Exec="$BINARY"
Icon=imagecompare
Terminal=false
Categories=Graphics;Viewer;
StartupWMClass=ImageCompare
DESKTOP_EOF

chmod +x "$DESKTOP_FILE"

if [ -d "$HOME/Desktop" ]; then
    cp "$DESKTOP_FILE" "$HOME/Desktop/imagecompare.desktop"
    chmod +x "$HOME/Desktop/imagecompare.desktop"
fi

command -v xdg-desktop-menu >/dev/null 2>&1 && \
    xdg-desktop-menu install --novendor "$DESKTOP_FILE" >/dev/null 2>&1 || true

command -v update-desktop-database >/dev/null 2>&1 && \
    update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && \
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true

for size in 16 32 48 64 128 256 512; do
    icon_file="$PROJECT_DIR/assets/icon_${size}.png"
    if [ -f "$icon_file" ]; then
        xdg-icon-resource install --novendor --size "$size" "$icon_file" imagecompare 2>/dev/null || true
    fi
done

echo "Installation complete."
echo "  → Search for 'Image Compare' in your application menu."
echo "  → You may need to log out and back in for the menu to refresh."
if [ -f "$HOME/Desktop/imagecompare.desktop" ]; then
    echo "  → Desktop shortcut: right-click → 'Allow Launching' (GNOME) to trust it."
fi
