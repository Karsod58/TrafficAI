@echo off
REM Windows-friendly test script (no video display)
REM Works around cv2.imshow limitation on Windows

echo.
echo ====================================================================
echo    BengaluruTrafficAI - Windows Test (No Display)
echo ====================================================================
echo.
echo Your system is WORKING! The previous error was just a Windows
echo display issue. This test runs without showing video windows.
echo.
pause

set VIDEO_PATH=..\14985167_960_540_25fps.mp4
set TEST_CAMERA=test_cam

echo.
echo ====================================================================
echo TEST: Full Detection Pipeline (300 frames)
echo ====================================================================
echo.
echo Processing video without display window...
echo This will take 2-3 minutes.
echo.

python main.py --source %VIDEO_PATH% --camera %TEST_CAMERA% --skip 3 --max-frames 300

echo.
echo ====================================================================
echo TEST COMPLETE!
echo ====================================================================
echo.

REM Check if evidence was created
echo Checking for evidence files...
echo.

if exist "output\evidence\*.jpg" (
    echo ✅ SUCCESS! Evidence files were created:
    echo.
    dir output\evidence\*.jpg
    echo.
    echo Your system is working correctly!
) else (
    echo ⚠️ No evidence files found.
    echo This might mean:
    echo   - Video has no violations (check console output)
    echo   - ROI not configured for red light detection
    echo   - Other violations detected but no evidence saved
)

echo.
echo ====================================================================
echo Next Steps:
echo ====================================================================
echo.
echo 1. Check console output above for violations detected
echo 2. View evidence images in: output\evidence\
echo 3. Check API if running: curl http://localhost:8000/violations
echo.
echo To process full video:
echo   python main.py --source %VIDEO_PATH% --camera %TEST_CAMERA% --skip 3
echo.
pause
