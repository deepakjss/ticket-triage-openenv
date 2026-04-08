#!/bin/bash
# Start Chrome with CDP port 9222 and open the Scaler hackathon dashboard.
# Then log in manually in that window. Only scripts on YOUR machine can attach
# (e.g. Playwright connect_over_cdp("http://127.0.0.1:9222")) — not remote control from Cursor.

DASHBOARD_URL="https://www.scaler.com/school-of-technology/meta-pytorch-hackathon/dashboard"
PROFILE_DIR="${HOME}/.chrome-debug-scaler"

echo "Quitting Chrome (if running) — required so debug flags apply..."
osascript -e 'quit app "Google Chrome"' 2>/dev/null
sleep 2

echo "Starting Chrome with --remote-debugging-port=9222..."
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --user-data-dir="$PROFILE_DIR" \
  "$DASHBOARD_URL" &

sleep 3
if curl -s http://127.0.0.1:9222/json/version >/dev/null 2>&1; then
  echo "OK: Debug port 9222 is up. Log in, then submit the form in this window."
else
  echo "If 9222 failed: wait a few seconds and run: curl -s http://127.0.0.1:9222/json/version"
fi
