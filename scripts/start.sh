#!/bin/bash
# Production startup script for Render
# Runs database seeding on first launch, then starts the API server.
set -e

echo "=== Movie RecSys API Startup ==="

# Check if DB has been seeded by looking for movies
SEED_CHECK=$(python -c "
import asyncio, os, sys
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
    echo "Database needs seeding..."
    cd /app
    python -c "
import asyncio, sys
sys.path.insert(0, '/app')
exec(open('scripts/seed_production.py').read())
asyncio.run(main())
"
    echo "Seeding complete."
else
    echo "Database already seeded, skipping."
fi

echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
