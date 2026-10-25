#!/usr/bin/env bash
set -euo pipefail

APP_NAME="Aria2 Download Manager"
SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/aria2-download-manager"
APP_FILE="$INSTALL_DIR/aria2_gui.py"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/aria2-download-manager.desktop"

echo "Installing required Fedora packages (aria2 and Python Tkinter)..."
sudo dnf install -y aria2 python3-tkinter

mkdir -p "$INSTALL_DIR" "$DESKTOP_DIR"
install -m 755 "$SOURCE_DIR/aria2_gui.py" "$APP_FILE"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Aria2 Download Manager
Comment=Multi-connection download manager powered by aria2
Exec=/usr/bin/python3 "$APP_FILE"
Icon=folder-download
Terminal=false
Categories=Network;FileTransfer;Utility;
StartupNotify=true
EOF

chmod 644 "$DESKTOP_FILE"
echo
echo "Installed successfully."
echo "Open the Activities overview and search for: Aria2 Download Manager"
echo "Or launch it with:"
echo "  python3 \"$APP_FILE\""
