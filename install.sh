#!/usr/bin/env bash
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${EUID}" -eq 0 ]]; then
    echo 'Ejecutá este instalador como tu usuario, sin sudo.' >&2
    exit 1
fi
if ! /usr/bin/python3 -c 'from gi.repository import Gio, GLib' 2>/dev/null; then
    case "${1:-}" in
        --check|--dry-run|--help|-h)
            echo 'Falta python3-gi. Instalalo con: sudo apt-get install python3-gi' >&2
            exit 1 ;;
        *) sudo apt-get install -y python3-gi ;;
    esac
fi
exec /usr/bin/python3 "${repo_dir}/scripts/installer.py" "$@"
