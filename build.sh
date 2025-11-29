#!/bin/bash

echo ""
echo "법수니 (beopsuny) 스킬 빌드"
echo ""

# Python 확인
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "[오류] Python이 설치되어 있지 않습니다."
    echo "Python을 설치해주세요: https://www.python.org/downloads/"
    exit 1
fi

# python3 우선, 없으면 python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
$PYTHON_CMD "$SCRIPT_DIR/build_skill.py" "$@"
