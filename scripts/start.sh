#!/bin/bash
# Production startup script
set -e

echo "=== Movie RecSys API Startup ==="
echo "PORT=${PORT:-8000}"

# Debug: print all env vars that look database/redis related (mask passwords)
echo "--- Environment variables (DB/Redis related) ---"
env | grep -iE "DATABASE|POSTGRES|PG|REDIS|RAILWAY" | sed 's/\(PASSWORD\|SECRET\|KEY\)=.*/\1=***masked***/' || true
echo "--- End env vars ---"

# Debug: check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL is not set!"
    echo "Falling back to defaults (will fail if no local DB)..."
else
    echo "DATABASE_URL is set (${#DATABASE_URL} chars, starts with: ${DATABASE_URL:0:20}...)"
fi

if [ -z "$REDIS_URL" ]; then
    echo "WARNING: REDIS_URL is not set, using default localhost"
else
    echo "REDIS_URL is set (${#REDIS_URL} chars)"
fi

# Start uvicorn
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" &
UVICORN_PID=$!

# Wait for the server to be ready
echo "Waiting for API server to start..."
for i in $(seq 1 60); do
    if curl -sf "http://localhost:${PORT:-8000}/api/v1/health" > /dev/null 2>&1; then
        echo "API server is up."
        break
    fi
    sleep 2
done

# Only attempt seeding if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "Skipping DB seed (no DATABASE_URL)"
else
    SEED_CHECK=$(python -c "
import asyncio, sys
sys.path.insert(0, '/app')
async def check():
    from app.core.database import async_session_factory, engine
    from sqlalchemy import text
    try:
        async with async_session_factory() as session:
            result = await session.execute(text('SELECT COUNT(*) FROM movies'))
            count = result.scalar()
            print(count or 0)
    except Exception as e:
        print(0, file=__import__('sys').stderr)
        print(0)
    finally:
        await engine.dispose()
asyncio.run(check())
" 2>/dev/null || echo "0")

    echo "Movies in DB: $SEED_CHECK"

    if [ "$SEED_CHECK" -lt 100 ]; then
        echo "Database needs seeding..."
        python scripts/seed_production.py || echo "Seeding failed, but server is running."
    else
        echo "Database already seeded, skipping."
    fi
fi

# Keep the container alive
wait $UVICORN_PID
