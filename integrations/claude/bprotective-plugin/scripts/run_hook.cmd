: << 'BATCH'
@echo off
setlocal EnableExtensions
set "HOOK=%~dp0before_shell.py"
where py >nul 2>&1
if not errorlevel 1 goto :runpy
where python >nul 2>&1
if not errorlevel 1 goto :runpython
where python3 >nul 2>&1
if not errorlevel 1 goto :runpython3
exit /b 0
:runpy
py -3 "%HOOK%" %*
exit /b %ERRORLEVEL%
:runpython
python "%HOOK%" %*
exit /b %ERRORLEVEL%
:runpython3
python3 "%HOOK%" %*
exit /b %ERRORLEVEL%
BATCH
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
hook="$here/before_shell.py"
if command -v python3 >/dev/null 2>&1; then
  exec python3 "$hook" "$@"
elif command -v python >/dev/null 2>&1; then
  exec python "$hook" "$@"
elif command -v py >/dev/null 2>&1; then
  exec py -3 "$hook" "$@"
fi
exit 0
