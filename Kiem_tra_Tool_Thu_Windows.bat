@echo off
call "%~dp0Mo_tool_Thu_Windows.bat" --diagnose %*
set "thu_exit=%errorlevel%"
if not "%TOOL_THU_NO_PAUSE%"=="1" pause
exit /b %thu_exit%

