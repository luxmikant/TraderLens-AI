@echo off
REM Tradl AI - Quick Docker Deployment Script for Windows

echo ========================================
echo   Tradl AI - Docker Deployment
echo ========================================

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running. Please start Docker Desktop.
    pause
    exit /b 1
)

echo.
echo [1/3] Building Docker image (first build ~10 min, rebuilds ~30 sec)...
docker build -t tradl-ai:latest .

if errorlevel 1 (
    echo ERROR: Docker build failed!
    pause
    exit /b 1
)

echo.
echo [2/3] Stopping any existing container...
docker stop tradl-api 2>nul
docker rm tradl-api 2>nul

echo.
echo [3/3] Starting Tradl AI container...
docker run -d ^
    --name tradl-api ^
    -p 8000:8000 ^
    --env-file .env ^
    -e ENVIRONMENT=production ^
    -v tradl-chroma:/app/chroma_db ^
    tradl-ai:latest

if errorlevel 1 (
    echo ERROR: Failed to start container!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Deployment Complete!
echo ========================================
echo.
echo API running at: http://localhost:8000
echo Health check:   http://localhost:8000/health
echo API docs:       http://localhost:8000/docs
echo.
echo View logs: docker logs -f tradl-api
echo Stop:      docker stop tradl-api
echo.

REM Wait for startup and test health
timeout /t 5 /nobreak >nul
echo Testing health endpoint...
curl -s http://localhost:8000/health

pause
