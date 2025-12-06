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


def get_api_keys() -> tuple[str, str, dict]:
    """API 키들을 입력받습니다."""
    print("=" * 50)
    print("법수니 (beopsuny) 스킬 빌드")
    print("=" * 50)
    print()

    # 1. 국가법령정보 OC 코드
    print("[1/3] 국가법령정보 공동활용 API")
    print("아직 없다면 https://open.law.go.kr 에서 회원가입 후")
    print("OpenAPI 신청을 하세요. (무료)")
    print()
    print("OC 코드는 가입한 이메일의 @ 앞부분입니다.")
    print("예: your_email@gmail.com → your_email")
    print()

    while True:
        oc_code = input("OC 코드를 입력하세요: ").strip()
        if oc_code:
            break
        print("OC 코드를 입력해주세요.")

    print()

    # 2. 열린국회정보 API 키
    print("[2/3] 열린국회정보 API (국회 의안 조회용)")
    print("아직 없다면 https://open.assembly.go.kr 에서 회원가입 후")
    print("인증키를 신청하세요. (무료)")
    print()
    print("(선택사항 - 국회 의안 조회 기능을 사용하지 않으면 Enter로 건너뛰기)")
    print()

    assembly_api_key = input("열린국회정보 API 키를 입력하세요: ").strip()

    print()

    # 3. 게이트웨이 설정 (해외 접근용)
    print("[3/3] 게이트웨이 설정 (해외 접근용)")
    print("한국 정부 API는 해외 IP를 차단합니다.")
    print("Claude Desktop이 해외 서버에서 실행될 경우 게이트웨이가 필요합니다.")
    print()
    print("cors-anywhere 기반 게이트웨이 URL과 API 키를 입력하세요.")
    print("(선택사항 - 국내에서만 사용하면 Enter로 건너뛰기)")
    print()

    gateway_config = {}
    gateway_url = input("게이트웨이 URL (예: https://your-gateway.example.com): ").strip()

    if gateway_url:
        gateway_api_key = input("게이트웨이 API 키 (선택, 인증 필요 시): ").strip()
        gateway_config = {
            "url": gateway_url,
            "api_key": gateway_api_key if gateway_api_key else None
        }
        print("게이트웨이 설정이 추가됩니다.")

    return oc_code, assembly_api_key, gateway_config


def create_settings_yaml(oc_code: str, assembly_api_key: str = "", gateway_config: dict = None) -> str:
    """settings.yaml 내용을 생성합니다."""
    assembly_line = f'assembly_api_key: "{assembly_api_key}"' if assembly_api_key else '# assembly_api_key: ""  # 열린국회정보 API 키 (https://open.assembly.go.kr)'

    # 게이트웨이 설정 생성
    if gateway_config and gateway_config.get("url"):
        api_key_line = f'  api_key: "{gateway_config.get("api_key")}"' if gateway_config.get("api_key") else '  # api_key: ""  # 게이트웨이 API 키 (인증 필요 시)'
        gateway_section = f'''
# 게이트웨이 설정 (해외 접근용)
# 한국 정부 API는 해외 IP를 차단합니다.
# cors-anywhere 기반 게이트웨이를 통해 접근합니다.
gateway:
  url: "{gateway_config.get('url')}"
{api_key_line}
'''
    else:
        gateway_section = '''
# 게이트웨이 설정 (해외 접근용)
# 한국 정부 API는 해외 IP를 차단합니다.
# cors-anywhere 기반 게이트웨이를 통해 접근합니다.
# gateway:
#   url: "https://your-gateway.example.com"
#   api_key: "your-api-key"  # 선택
'''

    return f'''# Korean Law API Configuration
# 국가법령정보 공동활용 API 설정

# OC Code (Open API Code)
# open.law.go.kr에서 발급받은 ID (이메일의 @ 앞부분)
oc_code: "{oc_code}"

# 열린국회정보 API Key (국회 의안 조회용)
# open.assembly.go.kr에서 발급받은 인증키
{assembly_line}

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
{gateway_section}'''


def build_zip(oc_code: str, assembly_api_key: str, output_path: Path, gateway_config: dict = None) -> None:
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

        # config/settings.yaml (API 키 및 게이트웨이 설정 주입)
        settings_content = create_settings_yaml(oc_code, assembly_api_key, gateway_config)
        zf.writestr("beopsuny/config/settings.yaml", settings_content)

        # config/law_index.yaml (법령 인덱스)
        law_index = skill_dir / "config" / "law_index.yaml"
        if law_index.exists():
            zf.write(law_index, "beopsuny/config/law_index.yaml")

        # scripts/*.py
        scripts_dir = skill_dir / "scripts"
        if scripts_dir.exists():
            for py_file in scripts_dir.glob("*.py"):
                zf.write(py_file, f"beopsuny/scripts/{py_file.name}")

        # data 디렉토리 구조 (빈 디렉토리용 .gitkeep)
        zf.writestr("beopsuny/data/raw/.gitkeep", "")
        zf.writestr("beopsuny/data/parsed/.gitkeep", "")
        zf.writestr("beopsuny/data/bills/.gitkeep", "")

    print()
    print(f"✓ 스킬 zip 파일이 생성되었습니다: {output_path}")
    print()
    print("사용 방법:")
    print("1. Claude Desktop 설정에서 Skills 메뉴로 이동")
    print("2. 'Add Skill' 클릭")
    print(f"3. 생성된 {output_path.name} 파일 선택")
    print()
    print("⚠️  주의: 이 zip 파일에는 개인 OC 코드가 포함되어 있습니다.")
    if gateway_config and gateway_config.get("api_key"):
        print("⚠️  주의: 게이트웨이 API 키도 포함되어 있습니다.")
    print("    다른 사람과 공유하지 마세요!")


def main():
    # 명령줄 인자로 API 키 받기
    oc_code = None
    assembly_api_key = None
    gateway_url = None
    gateway_api_key = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--oc-code", "-o") and i + 1 < len(args):
            oc_code = args[i + 1]
            i += 2
        elif arg.startswith("--oc-code="):
            oc_code = arg.split("=", 1)[1]
            i += 1
        elif arg in ("--assembly-key", "-a") and i + 1 < len(args):
            assembly_api_key = args[i + 1]
            i += 2
        elif arg.startswith("--assembly-key="):
            assembly_api_key = arg.split("=", 1)[1]
            i += 1
        elif arg in ("--gateway-url", "-g") and i + 1 < len(args):
            gateway_url = args[i + 1]
            i += 2
        elif arg.startswith("--gateway-url="):
            gateway_url = arg.split("=", 1)[1]
            i += 1
        elif arg in ("--gateway-key", "-k") and i + 1 < len(args):
            gateway_api_key = args[i + 1]
            i += 2
        elif arg.startswith("--gateway-key="):
            gateway_api_key = arg.split("=", 1)[1]
            i += 1
        elif arg in ("--help", "-h"):
            print("사용법: python build_skill.py [옵션]")
            print()
            print("옵션:")
            print("  -o, --oc-code=CODE       국가법령정보 OC 코드 (필수)")
            print("  -a, --assembly-key=KEY   열린국회정보 API 키 (선택)")
            print("  -g, --gateway-url=URL    게이트웨이 URL (선택, 해외 접근용)")
            print("                           예: https://your-gateway.example.com")
            print("  -k, --gateway-key=KEY    게이트웨이 API 키 (선택, 인증 필요 시)")
            print("  -h, --help               도움말 표시")
            print()
            print("예시:")
            print("  python build_skill.py")
            print("  python build_skill.py --oc-code=myoccode")
            print("  python build_skill.py -o myoccode -g https://my-gateway.com -k myapikey")
            sys.exit(0)
        else:
            i += 1

    # 게이트웨이 설정 구성
    gateway_config = {}
    if gateway_url:
        gateway_config = {"url": gateway_url, "api_key": gateway_api_key}

    # 인자 없으면 대화형으로 입력
    if not oc_code:
        oc_code, assembly_api_key, gateway_config = get_api_keys()

    # 출력 경로
    output_path = Path(__file__).parent / "beopsuny-skill.zip"

    # 기존 파일 확인
    if output_path.exists():
        response = input(f"{output_path.name} 파일이 이미 존재합니다. 덮어쓸까요? (y/N): ")
        if response.lower() != 'y':
            print("취소되었습니다.")
            sys.exit(0)

    build_zip(oc_code, assembly_api_key or "", output_path, gateway_config)


if __name__ == "__main__":
    main()
