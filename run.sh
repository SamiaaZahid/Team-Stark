#!/usr/bin/env bash
set -e
echo "========================================================"
echo "Starting NovaWorks Technologies - Node.js + React MVP"
echo "========================================================"

echo "1. Initializing and Seeding Database..."
cd backend
npx prisma db push
node prisma/seed.js

echo "2. Launching Backend and Frontend..."
node src/server.js &
BACKEND_PID=$!

cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "========================================================"
echo "Application successfully launched!"
echo "- Backend API: http://localhost:5000"
echo "- Frontend UI:  http://localhost:5173"
echo "========================================================"
echo ""

wait $BACKEND_PID $FRONTEND_PID
