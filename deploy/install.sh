#!/bin/bash
# Install systemd user units for mimir-webwright.
# Run from the repo root: bash deploy/install.sh
set -e

REPO_DIR="$(dirname "$(dirname "$(readlink -f "$0")")")"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

echo "Installing mimir-webwright systemd user units..."
mkdir -p "$SYSTEMD_USER_DIR"

cp "$REPO_DIR/deploy/systemd/"*.service "$REPO_DIR/deploy/systemd/"*.timer "$SYSTEMD_USER_DIR/"

systemctl --user daemon-reload

systemctl --user enable --now mimir-webwright-pisos.timer
systemctl --user enable --now mimir-webwright-football.timer

echo ""
echo "Timers installed and enabled."
echo ""
echo "Active timers:"
systemctl --user list-timers mimir-webwright-* --no-pager
