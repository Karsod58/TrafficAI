@echo off
REM Test script to analyze video quality and get recommendations
REM Usage: test_video_quality.bat path\to\video.mp4

setlocal

if "%~1"=="" (
    echo.
    echo Usage: test_video_quality.bat path\to\video.mp4
    echo.
    echo Example: test_video_quality.bat video_360p.mp4
    echo.
    exit /b 1
)

set VIDEO_PATH=%~1

if not exist "%VIDEO_PATH%" (
    echo.
    echo ERROR: Video file not found: %VIDEO_PATH%
    echo.
    exit /b 1
)

echo.
echo ==========================================
echo    Video Quality Analyzer
echo ==========================================
echo.

python core\low_res_handler.py "%VIDEO_PATH%"

echo.
echo ==========================================
echo    Quick Test Commands
echo ==========================================
echo.
echo To run detection on this video:
echo.
echo   python main.py --source "%VIDEO_PATH%" --camera demo_cam --show
echo.
echo To skip ALPR (faster for low-res):
echo.
echo   python main.py --source "%VIDEO_PATH%" --camera demo_cam --no-preproc --skip 5
echo.
echo.
pause
