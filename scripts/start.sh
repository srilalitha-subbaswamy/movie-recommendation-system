#!/bin/bash
# Production startup script
# Starts the API server immediately, then seeds the database in the background.
set -e

echo "=== Movie RecSys API Startup ==="
echo "PORT=${PORT:-8000}"

# Start uvicorn in the background first so healthcheck can pass
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" &
UVICORN_PID=$!

# Wait for the server to be ready
echo "Waiting for API server to start..."
for i in $(seq 1 30); do
    if curl -sf "http://localhost:${PORT:-8000}/api/v1/health" > /dev/null 2>&1; then
        echo "API server is up."
        break
    fi
    sleep 2
done

# Check if DB needs seeding
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
    except Exception:
        print(0)
    finally:
        await engine.dispose()
asyncio.run(check())
" 2>/dev/null || echo "0")

echo "Movies in DB: $SEED_CHECK"

if [ "$SEED_CHECK" -lt 100 ]; then
    echo "Database needs seeding (running in background)..."
    python -c "
import asyncio, sys
sys.path.insert(0, '/app')
exec(open('scripts/seed_production.py').read())
asyncio.run(main())
" &
    SEED_PID=$!
    # Wait for seeding to finish
    wait $SEED_PID
    echo "Seeding complete."
else
    echo "Database already seeded, skipping."
fi

# Wait for uvicorn (keep the container alive)
wait $UVICORN_PID
