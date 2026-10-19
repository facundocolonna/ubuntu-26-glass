#!/usr/bin/env bash
set -euo pipefail
bundle_dir="$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")"
trial_seconds=""
mode=""
case "${1:-}" in
  --autostart) mode=--autostart ;;
  --timed) trial_seconds=30 ;;
  --stop)
    systemctl --user stop littlebigmouse-trial.service 2>/dev/null || true
    systemctl --user stop littlebigmouse-preview.service 2>/dev/null || true
    exit 0 ;;
  --revoke)
    "$0" --stop
    exec pkexec /usr/bin/python3 "$bundle_dir/access.py" revoke "$(id -u)" ;;
  "") ;;
  *) printf 'Uso: %s [--autostart|--timed|--stop|--revoke]\n' "$0"; exit 2 ;;
esac
if systemctl --user is-active --quiet littlebigmouse-trial.service; then
  if [[ "$mode" == --autostart ]]; then exit 0; fi
  exec /usr/bin/python3 "$bundle_dir/launch.py" --show
fi
if [[ "$mode" != --autostart ]] && ! /usr/bin/python3 - <<'PY'
import os
from pathlib import Path
mice = [Path('/dev/input') / p.name for p in Path('/sys/class/input').glob('event*')
        if (p / 'device/name').read_text().strip() == 'Logitech MX Anywhere 3']
raise SystemExit(0 if os.access('/dev/uinput', os.R_OK | os.W_OK)
                 and any(os.access(p, os.R_OK | os.W_OK) for p in mice) else 1)
PY
then
  pkexec /usr/bin/python3 "$bundle_dir/access.py" grant "$(id -u)"
fi
systemctl --user stop littlebigmouse-preview.service 2>/dev/null || true
exec systemd-run --user --unit=littlebigmouse-trial --collect \
  --property=KillMode=control-group --property=PartOf=graphical-session.target \
  --property=Restart=on-failure --property=RestartSec=3 \
  --setenv="DISPLAY=${DISPLAY:-}" --setenv="XAUTHORITY=${XAUTHORITY:-}" \
  --setenv="WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-}" \
  --setenv=LBM_HOOK_UI=1 --setenv="LBM_EVDEV_AUTORELEASE_SECS=$trial_seconds" \
  /usr/bin/python3 "$bundle_dir/launch.py" ${mode:+"$mode"}
