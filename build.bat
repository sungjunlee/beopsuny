@echo off
chcp 65001 > nul
echo.
echo 법수니 (beopsuny) 스킬 빌드
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo Python을 설치해주세요: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

python "%~dp0build_skill.py" %*
pause
