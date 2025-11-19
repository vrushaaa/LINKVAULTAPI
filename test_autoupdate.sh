#!/bin/bash
set -e

echo "🔍 EC2 deployment health check..."

APP_DIR="/home/ubuntu/LINKVAULTAPI"

if [ ! -d "$APP_DIR" ]; then
  echo "❌ Repo directory missing at $APP_DIR"
  exit 1
fi
echo "✅ Repo exists"

cd $APP_DIR

git fetch || { echo "❌ git fetch failed"; exit 1; }
echo "✅ git fetch OK"

# Check Gunicorn systemd service (named linkvault)
systemctl is-active --quiet linkvault || { echo "❌ Gunicorn (linkvault) is not active"; exit 1; }
echo "✅ Gunicorn running"

systemctl is-active --quiet nginx || { echo "❌ Nginx is not active"; exit 1; }
echo "✅ Nginx running"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1/)
if [ "$STATUS" != "200" ]; then
  echo "❌ App not responding on 127.0.0.1 (status $STATUS)"
  exit 1
fi
echo "✅ App responding (127.0.0.1 -> 200)"

echo "🎉 EC2 auto-update health check PASSED!"
exit 0
