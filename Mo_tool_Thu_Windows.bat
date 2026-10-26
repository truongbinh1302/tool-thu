@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
py -3 -c "import sys;sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if not errorlevel 1 (
  py -3 -X utf8 start.py %*
  goto :finished
)
python -c "import sys;sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if not errorlevel 1 (
  python -X utf8 start.py %*
  goto :finished
)
echo Can cai Python 3.11 tro len tu python.org. Khi cai chon Add Python to PATH.
if not "%TOOL_THU_NO_PAUSE%"=="1" pause
exit /b 1
:finished
set "thu_exit=%errorlevel%"
if not "%thu_exit%"=="0" if not "%TOOL_THU_NO_PAUSE%"=="1" pause
exit /b %thu_exit%

