#!/bin/sh
# Boot sequence for the CRPP backend container.
#
# The SQLite file and the uploads directory are gitignored, so a fresh volume
# starts empty and the demo would come up with nothing on screen. seed_demo_data
# already guards itself: it exits 2 and changes nothing when tickets exist, so
# running it on every boot is safe and only does work the first time.
set -e

cd /app/backend

mkdir -p "$(dirname "${CRPP_DB_PATH:-/data/crpp.db}")" "${UPLOAD_DIR:-/data/uploads}"

if [ "${SEED_DEMO_DATA:-true}" = "true" ]; then
  echo "[boot] seeding demo data if the database is empty"
  set +e
  python seed_demo_data.py
  seed_status=$?
  set -e
  # 0 = seeded, 2 = already populated and deliberately left alone.
  if [ "$seed_status" -ne 0 ] && [ "$seed_status" -ne 2 ]; then
    echo "[boot] seed failed with status $seed_status" >&2
    exit "$seed_status"
  fi
fi

echo "[boot] starting uvicorn on 0.0.0.0:${PORT:-8080}"
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}"
