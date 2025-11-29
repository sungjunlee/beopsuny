#!/usr/bin/env python3
"""
법수니 (beopsuny) 스킬 빌드 스크립트
Claude Desktop용 zip 파일을 생성합니다.
"""

import os
import sys
import zipfile
import shutil
from pathlib import Path


def get_oc_code() -> str:
    """OC 코드를 입력받습니다."""
    print("=" * 50)
    print("법수니 (beopsuny) 스킬 빌드")
    print("=" * 50)
    print()
    print("국가법령정보 공동활용 API의 OC 코드가 필요합니다.")
    print("아직 없다면 https://open.law.go.kr 에서 회원가입 후")
    print("OpenAPI 신청을 하세요. (무료)")
    print()
    print("OC 코드는 가입한 이메일의 @ 앞부분입니다.")
    print("예: your_email@gmail.com → your_email")
    print()

    while True:
        oc_code = input("OC 코드를 입력하세요: ").strip()
        if oc_code:
            return oc_code
        print("OC 코드를 입력해주세요.")


def create_settings_yaml(oc_code: str) -> str:
    """settings.yaml 내용을 생성합니다."""
    return f'''# Korean Law API Configuration
# 국가법령정보 공동활용 API 설정

# OC Code (Open API Code)
# open.law.go.kr에서 발급받은 ID (이메일의 @ 앞부분)
oc_code: "{oc_code}"

# API Settings
api:
  base_url: "http://www.law.go.kr/DRF"
  timeout: 30
  default_display: 20  # 기본 검색 결과 수

# 검색 대상 코드
targets:
  law: "법령"
  prec: "판례"
  ordin: "자치법규"
  admrul: "행정규칙"
  expc: "법령해석례"
  detc: "헌재결정례"
'''


def build_zip(oc_code: str, output_path: Path) -> None:
    """스킬 zip 파일을 생성합니다."""
    script_dir = Path(__file__).parent
    skill_dir = script_dir / ".claude" / "skills" / "beopsuny"

    if not skill_dir.exists():
        print(f"오류: 스킬 디렉토리를 찾을 수 없습니다: {skill_dir}")
        sys.exit(1)

    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # SKILL.md
        skill_md = skill_dir / "SKILL.md"
        if skill_md.exists():
            zf.write(skill_md, "beopsuny/SKILL.md")

        # config/settings.yaml (OC 코드 주입)
        settings_content = create_settings_yaml(oc_code)
        zf.writestr("beopsuny/config/settings.yaml", settings_content)

        # scripts/*.py
        scripts_dir = skill_dir / "scripts"
        if scripts_dir.exists():
            for py_file in scripts_dir.glob("*.py"):
                zf.write(py_file, f"beopsuny/scripts/{py_file.name}")

        # data 디렉토리 구조 (빈 디렉토리용 .gitkeep)
        zf.writestr("beopsuny/data/raw/.gitkeep", "")
        zf.writestr("beopsuny/data/parsed/.gitkeep", "")

    print()
    print(f"✓ 스킬 zip 파일이 생성되었습니다: {output_path}")
    print()
    print("사용 방법:")
    print("1. Claude Desktop 설정에서 Skills 메뉴로 이동")
    print("2. 'Add Skill' 클릭")
    print(f"3. 생성된 {output_path.name} 파일 선택")
    print()
    print("⚠️  주의: 이 zip 파일에는 개인 OC 코드가 포함되어 있습니다.")
    print("    다른 사람과 공유하지 마세요!")


def main():
    # 명령줄 인자로 OC 코드 받기
    oc_code = None
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg in ("--oc-code", "-o") and i < len(sys.argv) - 1:
            oc_code = sys.argv[i + 1]
            break
        elif arg.startswith("--oc-code="):
            oc_code = arg.split("=", 1)[1]
            break

    # 인자 없으면 대화형으로 입력
    if not oc_code:
        oc_code = get_oc_code()

    # 출력 경로
    output_path = Path(__file__).parent / "beopsuny-skill.zip"

    # 기존 파일 확인
    if output_path.exists():
        response = input(f"{output_path.name} 파일이 이미 존재합니다. 덮어쓸까요? (y/N): ")
        if response.lower() != 'y':
            print("취소되었습니다.")
            sys.exit(0)

    build_zip(oc_code, output_path)


if __name__ == "__main__":
    main()
