@echo off
echo ========================================================
echo Starting NovaWorks Technologies - Node.js + React MVP
echo ========================================================
set "PATH=%ProgramFiles%\nodejs;%APPDATA%\npm;%PATH%"

echo 1. Initializing and Seeding Database...
cd backend
call npx.cmd prisma db push
call node prisma/seed.js

echo 2. Launching Backend on Port 5000...
start "NovaWorks Backend (Port 5000)" cmd /k "node src/server.js"

echo 3. Launching React Vite Frontend on Port 5174...
cd ..\frontend
start "NovaWorks Frontend (Port 5174)" cmd /k "npm.cmd run dev"

echo.
echo ========================================================
echo Application successfully launched!
echo - Backend API: http://localhost:5000
echo - Frontend UI:  http://localhost:5174
echo ========================================================
echo.
pause
