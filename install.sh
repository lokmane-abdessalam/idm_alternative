#!/usr/bin/env bash
set -euo pipefail

APP_NAME="Aria2 Download Manager"
SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/aria2-download-manager"
APP_FILE="$INSTALL_DIR/aria2_gui.py"
LOGO_NAME="downloads-icon-android-lollipop.png"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/aria2-download-manager.desktop"

echo "Installing required Fedora packages (aria2 and Python Tkinter)..."
sudo dnf install -y aria2 python3-tkinter

mkdir -p "$INSTALL_DIR" "$DESKTOP_DIR"
install -m 755 "$SOURCE_DIR/aria2_gui.py" "$APP_FILE"

# Accept the logo next to this installer or in the user's Downloads folder.
LOGO_SOURCE=""
if [[ -f "$SOURCE_DIR/$LOGO_NAME" ]]; then
    LOGO_SOURCE="$SOURCE_DIR/$LOGO_NAME"
elif [[ -f "$HOME/Downloads/$LOGO_NAME" ]]; then
    LOGO_SOURCE="$HOME/Downloads/$LOGO_NAME"
fi

if [[ -n "$LOGO_SOURCE" ]]; then
    install -m 644 "$LOGO_SOURCE" "$INSTALL_DIR/$LOGO_NAME"
    ICON_LINE="Icon=$INSTALL_DIR/$LOGO_NAME"
    echo "Custom PNG logo installed."
else
    ICON_LINE="Icon=folder-download"
    echo "Logo not found. The app will install with its default icon."
    echo "To add your logo, place $LOGO_NAME next to install.sh or in ~/Downloads,"
    echo "then run ./install.sh again."
fi

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Aria2 Download Manager
Comment=Multi-connection download manager powered by aria2
Exec=/usr/bin/python3 "$APP_FILE"
$ICON_LINE
Terminal=false
Categories=Network;FileTransfer;Utility;
StartupNotify=true
EOF

chmod 644 "$DESKTOP_FILE"
echo
echo "Installed successfully."
echo "Open Activities and search for: Aria2 Download Manager"
echo "Or launch it with:"
echo "  python3 \"$APP_FILE\""
