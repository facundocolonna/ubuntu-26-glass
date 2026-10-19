#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
test_dir="$(mktemp -d)"
trap 'rm -rf -- "$test_dir"' EXIT
ln -s "$repo_dir/tests/headless-prepare.py" "$test_dir/prepare.py"
timeout -k 5s 45s dbus-run-session -- env GDK_BACKEND=wayland \
    gnome-shell-test-tool --headless \
    --wrap "/usr/bin/python3 $test_dir/prepare.py" \
    "$repo_dir/tests/focus-slider.js"
