#!/bin/sh
# Mobile Celery worker readiness: broker + mobile queue worker ping.
set -eu

python - <<'PY'
import os
import sys

import redis

url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
try:
    redis.from_url(url, socket_connect_timeout=3).ping()
except Exception:
    sys.exit(1)
PY

celery -A app.tasks.celery_app inspect ping --timeout=5 2>/dev/null | grep -q '"ok"'
