: << 'BATCH_OR_BASH'
@echo off
setlocal
set PYTHONIOENCODING=utf-8
set SCRIPT_DIR=%~dp0

rem Windows CLI launcher for Wedding Reception Serverless Grading
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python 3.10+ is required but was not found in PATH.
    pause
    exit /b 1
)

python "%SCRIPT_DIR%grading\grade.py" %*
set EXIT_CODE=%errorlevel%

if "%~1"=="" (
    echo.
    pause
)
exit /b %EXIT_CODE%
BATCH_OR_BASH

# =============================================================================
# Git Bash / Unix Shell Polyglot Fallback
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONIOENCODING=utf-8
if command -v python3 >/dev/null 2>&1; then
    exec python3 "$SCRIPT_DIR/grading/grade.py" "$@"
else
    exec python "$SCRIPT_DIR/grading/grade.py" "$@"
fi
