#!/bin/bash
set -e

echo "=== AI Agent Entrypoint ==="

# PostgreSQL 준비 대기
echo "Waiting for PostgreSQL..."
until pg_isready -h "${POSTGRES_HOST:-postgres}" -p "${POSTGRES_PORT:-5432}" -U "${POSTGRES_USER:-postgres}"; do
  sleep 1
done
echo "PostgreSQL is ready."

# 데모 데이터 존재 여부 확인 (campaigns 10개 미만이면 신규 설치로 판단)
CAMPAIGN_COUNT=$(psql "postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@${POSTGRES_HOST:-postgres}:${POSTGRES_PORT:-5432}/${POSTGRES_DB:-ai_agent}" \
  -t -c "SELECT COUNT(*) FROM campaigns;" 2>/dev/null | tr -d ' \n' || echo "0")

echo "Current campaign count: ${CAMPAIGN_COUNT}"

if [ "${CAMPAIGN_COUNT}" -lt "10" ] 2>/dev/null; then
  echo "Demo data not found. Running seed script..."
  python scripts/seed_demo_data.py && echo "Demo data seeded successfully." \
    || echo "Warning: Seed script failed (check GCP credentials). Starting server anyway."
else
  echo "Demo data already exists. Skipping seed."
fi

# FastAPI 서버 시작
echo "Starting FastAPI server..."
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
