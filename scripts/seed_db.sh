#!/bin/bash
# Seed the database with sample data
# Usage: bash scripts/seed_db.sh

set -euo pipefail

echo "=== Seeding Database ==="

# Run migrations first
echo "Running database migrations..."
cd api && alembic upgrade head

# Run seed script
echo "Seeding sample data..."
python -m app.scripts.seed_db

echo "Database seeded successfully!"
