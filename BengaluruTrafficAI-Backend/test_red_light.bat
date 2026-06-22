@echo off
REM Quick test script for red light detection debugging
REM Usage: test_red_light.bat path\to\video.mp4

setlocal enabledelayedexpansion

echo.
echo ==========================================
echo    Red Light Detection Test Suite
echo ==========================================
echo.

if "%~1"=="" (
    echo ERROR: No video path provided
    echo.
    echo Usage: test_red_light.bat path\to\video.mp4
    echo Example: test_red_light.bat ..\14985167_960_540_25fps.mp4
    echo.
    exit /b 1
)

set VIDEO_PATH=%~1

if not exist "%VIDEO_PATH%" (
    echo ERROR: Video file not found: %VIDEO_PATH%
    echo.
    exit /b 1
)

echo Video: %VIDEO_PATH%
echo.

REM Step 1: Test signal detection
echo ==========================================
echo Step 1: Testing Signal Detection
echo ==========================================
echo.

python test_signal_detection.py "%VIDEO_PATH%" 100

if errorlevel 1 (
    echo.
    echo ERROR: Signal detection test failed
    echo Check if Python and dependencies are installed
    exit /b 1
)

echo.
echo Press any key to continue with ROI setup...
pause > nul

REM Step 2: ROI Setup
echo.
echo ==========================================
echo Step 2: Interactive ROI Setup
echo ==========================================
echo.
echo Instructions:
echo   1. Click 4 corners of junction area (signal box)
echo   2. Press 'n' to continue
echo   3. Click 2 points for stop line
echo   4. Press 's' to save
echo   5. Or press 'q' to skip
echo.
echo Press any key to start ROI setup...
pause > nul

python tools\quick_roi_setup.py "%VIDEO_PATH%"

if errorlevel 1 (
    echo.
    echo WARNING: ROI setup failed or was skipped
    echo Will use default ROI configuration
    set USE_DEFAULT_ROI=1
) else (
    set USE_DEFAULT_ROI=0
)

REM Step 3: Run detection
echo.
echo ==========================================
echo Step 3: Running Red Light Detection
echo ==========================================
echo.

REM Get video filename without path
for %%F in ("%VIDEO_PATH%") do set VIDEO_NAME=%%~nF

if !USE_DEFAULT_ROI! equ 1 (
    echo Using default ROI configuration...
    echo.
    python main.py --source "%VIDEO_PATH%" --camera demo_cam --show --skip 2
) else (
    echo Using custom ROI: rois\%VIDEO_NAME%_roi.json
    echo.
    python main.py --source "%VIDEO_PATH%" --camera demo_cam --roi rois\%VIDEO_NAME%_roi.json --show --skip 2
)

echo.
echo ==========================================
echo Test Complete!
echo ==========================================
echo.
echo Check results:
echo   - Evidence images: output\evidence\
echo   - ROI config: rois\%VIDEO_NAME%_roi.json
echo.

pause
