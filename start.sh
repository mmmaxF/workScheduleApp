#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

if [ ! -f .env ]; then
  cat > .env <<'EOF'
APP_PORT=8000
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
LOG_MAX_BYTES=1048576
LOG_BACKUP_COUNT=5

POSTGRES_DB=headless_calendar_db
POSTGRES_USER=headless_calendar_user
POSTGRES_PASSWORD=要設定_PostgreSQLのパスワードを入力してください
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql://headless_calendar_user:要設定_PostgreSQLのパスワードを入力してください@postgres:5432/headless_calendar_db
EOF
  echo ".env を作成しました。要設定_ の値を設定してください。"
fi

if grep -q "要設定_" .env; then
  echo "警告: .env に 要設定_ が残っています。"
  echo "起動前に POSTGRES_PASSWORD と DATABASE_URL のパスワード部分を同じ値に修正してください。"
  echo "例: POSTGRES_PASSWORD=your_password"
  echo "例: DATABASE_URL=postgresql://headless_calendar_user:your_password@postgres:5432/headless_calendar_db"
  exit 1
fi

mkdir -p logs

docker compose down
docker compose build --no-cache
docker compose up -d
docker compose ps

echo ""
echo "起動しました。"
echo "Web UI: http://localhost:${APP_PORT:-8000}/calendar"
echo "API docs: http://localhost:${APP_PORT:-8000}/docs"
echo "ログ確認: docker compose logs -f web"
echo "アプリログ: tail -f logs/app.log"
