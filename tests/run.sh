#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
test_dir="$(mktemp -d)"
trap 'rm -rf -- "$test_dir"' EXIT
dbus-run-session -- env GSETTINGS_BACKEND=keyfile \
    XDG_DATA_HOME="$test_dir/data" XDG_CONFIG_HOME="$test_dir/config" \
    /usr/bin/python3 "$repo_dir/tests/roundtrip.py"
