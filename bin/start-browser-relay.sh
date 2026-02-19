#!/bin/bash
# Ford Perfect Browser Relay - Stable Launcher
# Starts Chromium as agency1 with proper environment

set -e

PROFILE="/opt/ai-orchestrator/var/chromium-profile"
LOG="/opt/ai-orchestrator/var/logs/browser-relay.log"
PIDFILE="/opt/ai-orchestrator/var/run/browser-relay.pid"

# Cleanup old locks
cleanup() {
    rm -rf /tmp/org.chromium.* 2>/dev/null || true
    rm -f "$PROFILE/SingletonLock" 2>/dev/null || true
}

# Kill old instances
pkill -9 chromium 2>/dev/null || true
sleep 2
cleanup

# Start Chromium as agency1 with full environment
echo "$(date): Starting browser relay..." >> "$LOG"

su - agency1 << 'SU_EOF'
export WAYLAND_DISPLAY=wayland-0
export XDG_RUNTIME_DIR=/run/user/1000
export DISPLAY=:0
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/1000/bus"

cd /opt/ai-orchestrator/var/chromium-profile

# Remove any remaining locks
rm -f SingletonLock SingletonCookie 2>/dev/null || true

# Start browser
exec /usr/lib/chromium/chromium \
  --ozone-platform=wayland \
  --user-data-dir=/opt/ai-orchestrator/var/chromium-profile \
  --password-store=basic \
  --no-sandbox \
  --remote-debugging-port=9222 \
  --remote-debugging-address=0.0.0.0 \
  --remote-allow-origins=* \
  --disable-gpu-compositing \
  --disable-software-rasterizer \
  https://takeout.google.com

SU_EOF

echo "$!" > "$PIDFILE"
echo "$(date): Browser started with PID $(cat $PIDFILE)" >> "$LOG"
