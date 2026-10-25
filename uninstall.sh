#!/usr/bin/env bash
set -euo pipefail
rm -rf "$HOME/.local/share/aria2-download-manager"
rm -f "$HOME/.local/share/applications/aria2-download-manager.desktop"
echo "Aria2 Download Manager was removed. aria2 itself was left installed."
