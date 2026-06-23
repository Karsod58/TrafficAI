@echo off
REM Comprehensive system test suite
REM Run this in your terminal with venv activated

setlocal enabledelayedexpansion

echo.
echo ====================================================================
echo    BengaluruTrafficAI - System Test Suite
echo ====================================================================
echo.
echo This will run a series of tests to verify the system is working.
echo Make sure you are in the activated venv!
echo.
echo Press Ctrl+C to cancel, or
pause

set VIDEO_PATH=..\14985167_960_540_25fps.mp4
set TEST_CAMERA=test_cam
set RESULTS_FILE=test_results.txt

echo. > %RESULTS_FILE%
echo BengaluruTrafficAI Test Results >> %RESULTS_FILE%
echo Generated: %DATE% %TIME% >> %RESULTS_FILE%
echo. >> %RESULTS_FILE%

REM ====================
REM Test 1: Quality Analysis
REM ====================
echo.
echo ====================================================================
echo TEST 1: Video Quality Analysis
echo ====================================================================
echo.

python core\low_res_handler.py %VIDEO_PATH% 2>&1 | tee -a %RESULTS_FILE%

if errorlevel 1 (
    echo [FAIL] Quality analysis failed >> %RESULTS_FILE%
    echo.
    echo ❌ TEST 1 FAILED - Quality analysis error
    echo Check that OpenCV is installed: pip install opencv-python
    echo.
) else (
    echo [PASS] Quality analysis completed >> %RESULTS_FILE%
    echo.
    echo ✅ TEST 1 PASSED
    echo.
)

echo Press any key to continue to Test 2...
pause > nul

REM ====================
REM Test 2: Signal Detection
REM ====================
echo.
echo ====================================================================
echo TEST 2: Red Light Signal Detection
echo ====================================================================
echo.

python test_signal_detection.py %VIDEO_PATH% 50 2>&1 | tee -a %RESULTS_FILE%

if errorlevel 1 (
    echo [FAIL] Signal detection failed >> %RESULTS_FILE%
    echo.
    echo ❌ TEST 2 FAILED - Signal detection error
    echo.
) else (
    echo [PASS] Signal detection completed >> %RESULTS_FILE%
    echo.
    echo ✅ TEST 2 PASSED
    echo.
)

echo Press any key to continue to Test 3...
pause > nul

REM ====================
REM Test 3: Quick Detection Test
REM ====================
echo.
echo ====================================================================
echo TEST 3: Quick Detection Test (300 frames, with video window)
echo ====================================================================
echo.
echo This will process 300 frames and show the video window.
echo Press 'Q' in the video window to stop early.
echo.

python main.py --source %VIDEO_PATH% --camera %TEST_CAMERA% --skip 3 --max-frames 300 --show 2>&1 | tee -a %RESULTS_FILE%

if errorlevel 1 (
    echo [FAIL] Quick detection test failed >> %RESULTS_FILE%
    echo.
    echo ❌ TEST 3 FAILED - Detection error
    echo.
) else (
    echo [PASS] Quick detection completed >> %RESULTS_FILE%
    echo.
    echo ✅ TEST 3 PASSED
    echo.
)

REM Check if evidence was created
if exist "output\evidence\*.jpg" (
    echo [PASS] Evidence files created >> %RESULTS_FILE%
    echo ✅ Evidence files were created
    dir output\evidence\ | find ".jpg"
) else (
    echo [WARN] No evidence files found >> %RESULTS_FILE%
    echo ⚠️ No evidence files found (may be normal if no violations)
)

echo.
echo Press any key to continue to Test 4...
pause > nul

REM ====================
REM Test 4: Performance Test
REM ====================
echo.
echo ====================================================================
echo TEST 4: Performance Test (500 frames, no video window)
echo ====================================================================
echo.
echo This will test processing performance without display.
echo.

python main.py --source %VIDEO_PATH% --camera %TEST_CAMERA% --skip 3 --max-frames 500 2>&1 | tee -a %RESULTS_FILE%

if errorlevel 1 (
    echo [FAIL] Performance test failed >> %RESULTS_FILE%
    echo.
    echo ❌ TEST 4 FAILED
    echo.
) else (
    echo [PASS] Performance test completed >> %RESULTS_FILE%
    echo.
    echo ✅ TEST 4 PASSED
    echo.
)

REM ====================
REM Test Summary
REM ====================
echo.
echo ====================================================================
echo TEST SUMMARY
echo ====================================================================
echo.

echo. >> %RESULTS_FILE%
echo ==================================================================== >> %RESULTS_FILE%
echo TEST SUMMARY >> %RESULTS_FILE%
echo ==================================================================== >> %RESULTS_FILE%

REM Count passes and fails
findstr /C:"[PASS]" %RESULTS_FILE% > nul
if not errorlevel 1 (
    for /f %%A in ('findstr /C:"[PASS]" %RESULTS_FILE% ^| find /C "[PASS]"') do set PASSED=%%A
) else (
    set PASSED=0
)

findstr /C:"[FAIL]" %RESULTS_FILE% > nul
if not errorlevel 1 (
    for /f %%A in ('findstr /C:"[FAIL]" %RESULTS_FILE% ^| find /C "[FAIL]"') do set FAILED=%%A
) else (
    set FAILED=0
)

echo Tests Passed: %PASSED% >> %RESULTS_FILE%
echo Tests Failed: %FAILED% >> %RESULTS_FILE%
echo. >> %RESULTS_FILE%

echo Tests Passed: %PASSED%
echo Tests Failed: %FAILED%
echo.

if %FAILED% EQU 0 (
    echo ✅ ALL TESTS PASSED! System is working correctly.
    echo ✅ ALL TESTS PASSED! >> %RESULTS_FILE%
) else (
    echo ⚠️ Some tests failed. Check test_results.txt for details.
    echo ⚠️ SOME TESTS FAILED >> %RESULTS_FILE%
)

echo.
echo Full results saved to: %RESULTS_FILE%
echo.

REM ====================
REM File Check
REM ====================
echo.
echo ====================================================================
echo FILE VERIFICATION
echo ====================================================================
echo.

echo Checking system files...
echo.

if exist "yolo11s.pt" (
    echo ✅ yolo11s.pt found
    echo [PASS] YOLO11 model found >> %RESULTS_FILE%
) else (
    echo ❌ yolo11s.pt NOT FOUND
    echo [FAIL] YOLO11 model missing >> %RESULTS_FILE%
)

if exist "output\evidence\" (
    echo ✅ Evidence folder exists
    for /f %%A in ('dir /b output\evidence\*.jpg 2^>nul ^| find /C ".jpg"') do set EVIDENCE_COUNT=%%A
    echo    Evidence files: %EVIDENCE_COUNT%
    echo [INFO] Evidence files: %EVIDENCE_COUNT% >> %RESULTS_FILE%
) else (
    echo ⚠️ Evidence folder not found
    echo [WARN] Evidence folder missing >> %RESULTS_FILE%
)

if exist "%VIDEO_PATH%" (
    echo ✅ Test video found
    echo [PASS] Test video exists >> %RESULTS_FILE%
) else (
    echo ❌ Test video NOT FOUND: %VIDEO_PATH%
    echo [FAIL] Test video missing >> %RESULTS_FILE%
)

echo.
echo ====================================================================
echo TESTING COMPLETE
echo ====================================================================
echo.
echo Next steps:
echo   1. Review test_results.txt for detailed output
echo   2. Check output\evidence\ for violation images
echo   3. If API is running, test: curl http://localhost:8000/violations
echo.
echo To run individual tests, see SYSTEM_TEST_GUIDE.md
echo.
pause
