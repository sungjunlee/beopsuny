#!/usr/bin/env python3
"""
Korean Law Fetcher - 국가법령정보센터 API 클라이언트

Usage:
    python fetch_law.py search "검색어" [--type law|prec|ordin|admrul|expc|detc]
    python fetch_law.py cases "검색어" [--court 대법원|고등|지방] [--from YYYYMMDD]
    python fetch_law.py fetch --id 법령ID [--with-decree]
    python fetch_law.py fetch --name "법령명" [--with-decree]
    python fetch_law.py recent [--days 30] [--from YYYYMMDD] [--to YYYYMMDD]
"""

import argparse
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

import yaml

# 게이트웨이 유틸리티 (해외 접근 지원)
try:
    from gateway import fetch_url, is_gateway_configured
    HAS_GATEWAY = True
except ImportError:
    HAS_GATEWAY = False

# 스크립트 위치 기준으로 경로 설정
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_PATH = SKILL_DIR / "config" / "settings.yaml"
LAW_INDEX_PATH = SKILL_DIR / "config" / "law_index.yaml"
DATA_RAW_DIR = SKILL_DIR / "data" / "raw"
DATA_PARSED_DIR = SKILL_DIR / "data" / "parsed"

# API 기본 URL
BASE_URL = "http://www.law.go.kr/DRF"

# 환경변수 이름
ENV_OC_CODE = "BEOPSUNY_OC_CODE"

# 캐시
_config_cache = None
_law_index_cache = None


def _load_config_file():
    """설정 파일 로드 (캐싱)"""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            _config_cache = yaml.safe_load(f) or {}
    else:
        _config_cache = {}

    return _config_cache


def _load_law_index():
    """법령 인덱스 파일 로드 (캐싱)"""
    global _law_index_cache
    if _law_index_cache is not None:
        return _law_index_cache

    if LAW_INDEX_PATH.exists():
        with open(LAW_INDEX_PATH, 'r', encoding='utf-8') as f:
            _law_index_cache = yaml.safe_load(f) or {}
    else:
        _law_index_cache = {}

    return _law_index_cache


def load_config():
    """OC 코드 로드 (환경변수 > 설정파일)"""
    # 1. 환경변수 우선
    oc_code = os.environ.get(ENV_OC_CODE)
    if oc_code:
        return oc_code

    # 2. 설정 파일 fallback
    config = _load_config_file()
    oc_code = config.get('oc_code', '')

    if not oc_code:
        print(f"Error: OC code not found.", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"Set one of the following:", file=sys.stderr)
        print(f"  1. Environment variable: export {ENV_OC_CODE}=your_oc_code", file=sys.stderr)
        print(f"  2. Config file: {CONFIG_PATH}", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"Get your OC code at: https://open.law.go.kr", file=sys.stderr)
        sys.exit(1)

    return oc_code


def get_major_law_id(name: str) -> str | None:
    """주요 법령의 ID를 law_index.yaml에서 조회"""
    law_index = _load_law_index()
    major_laws = law_index.get('major_laws', {})

    # 정확한 이름으로 먼저 검색
    if name in major_laws:
        return major_laws[name]

    # 공백 제거 후 검색
    clean_name = name.replace(' ', '')
    for law_name, law_id in major_laws.items():
        if law_name.replace(' ', '') == clean_name:
            return law_id

    return None


def api_request(endpoint: str, params: dict) -> ET.Element:
    """API 요청 및 XML 파싱 (게이트웨이 자동 사용)"""
    url = f"{BASE_URL}/{endpoint}?{urllib.parse.urlencode(params)}"

    try:
        # 게이트웨이 유틸리티 사용 (설정되어 있으면 자동 사용)
        if HAS_GATEWAY:
            try:
                content = fetch_url(url, timeout=30)
            except ValueError as e:
                # 게이트웨이 미설정 시 직접 시도
                print(f"Note: {e}", file=sys.stderr)
                print("Attempting direct connection...", file=sys.stderr)
                content = None

            if content is not None:
                # HTML 응답 감지
                if content.strip().startswith('<!DOCTYPE') or content.strip().startswith('<html'):
                    print(f"Error: API returned HTML instead of XML.", file=sys.stderr)
                    print(f"This usually means overseas access is blocked.", file=sys.stderr)
                    print(f"", file=sys.stderr)
                    print(f"Solution: Configure cors-anywhere gateway:", file=sys.stderr)
                    print(f"  export BEOPSUNY_GATEWAY_URL='https://your-gateway.example.com'", file=sys.stderr)
                    sys.exit(1)

                return ET.fromstring(content)

        # 직접 접근 (게이트웨이 미설정)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode('utf-8')

            # HTML 응답 감지 (API 오류 시 HTML 반환됨)
            if content.strip().startswith('<!DOCTYPE') or content.strip().startswith('<html'):
                print(f"Error: API returned HTML instead of XML.", file=sys.stderr)
                print(f"This usually means overseas access is blocked.", file=sys.stderr)
                print(f"", file=sys.stderr)
                print(f"Solution: Configure cors-anywhere gateway:", file=sys.stderr)
                print(f"  export BEOPSUNY_GATEWAY_URL='https://your-gateway.example.com'", file=sys.stderr)
                print(f"", file=sys.stderr)
                print(f"URL: {url}", file=sys.stderr)
                sys.exit(1)

            return ET.fromstring(content)
    except urllib.error.HTTPError as e:
        print(f"Error: HTTP {e.code} - {e.reason}", file=sys.stderr)
        if e.code == 403:
            print(f"", file=sys.stderr)
            print(f"403 Forbidden - overseas access may be blocked.", file=sys.stderr)
            print(f"Configure gateway: export BEOPSUNY_GATEWAY_URL='https://...'", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: API request failed - {e}", file=sys.stderr)
        sys.exit(1)
    except ET.ParseError as e:
        print(f"Error: Failed to parse XML response - {e}", file=sys.stderr)
        print(f"", file=sys.stderr)
        print(f"This may indicate the API returned an error page instead of XML.", file=sys.stderr)
        print(f"URL: {url}", file=sys.stderr)
        sys.exit(1)


def search_laws(query: str, target: str = "law", display: int = 20, page: int = 1, sort: str = None):
    """
    법령 검색

    Args:
        query: 검색어
        target: 검색 대상 (law: 법령, prec: 판례, ordin: 자치법규, admrul: 행정규칙, expc: 법령해석례, detc: 헌재결정례)
        display: 결과 개수 (최대 100)
        page: 페이지 번호
        sort: 정렬 기준 (date: 날짜순, name: 이름순)
    """
    oc = load_config()

    params = {
        'OC': oc,
        'target': target,
        'type': 'XML',
        'query': query,
        'display': display,
        'page': page,
    }

    if sort:
        params['sort'] = sort

    root = api_request('lawSearch.do', params)

    # 결과 파싱 - target에 따라 다른 태그 사용
    total = root.findtext('.//totalCnt', '0')

    target_names = {
        'law': '법령', 'prec': '판례', 'ordin': '자치법규',
        'admrul': '행정규칙', 'expc': '법령해석례', 'detc': '헌재결정례'
    }
    target_name = target_names.get(target, target)
    print(f"\n=== {target_name} 검색 결과: '{query}' (총 {total}건) ===\n")

    results = []

    # 판례 검색
    if target == 'prec':
        for item in root.findall('.//prec'):
            case_id = item.findtext('판례일련번호', '')
            case_name = item.findtext('사건명', '')
            case_number = item.findtext('사건번호', '')
            court_name = item.findtext('법원명', '')
            judge_date = item.findtext('선고일자', '')
            case_type = item.findtext('사건종류명', '')

            results.append({
                'id': case_id,
                'name': case_name,
                'case_number': case_number,
                'court': court_name,
                'judge_date': judge_date,
                'type': case_type,
            })

            print(f"⚖️  {case_name}")
            print(f"   사건번호: {case_number}")
            print(f"   법원: {court_name} | 선고일: {judge_date}")
            print(f"   사건종류: {case_type}")
            print(f"   링크: https://www.law.go.kr/판례/({case_number.replace(' ', '')})")
            print()

    # 행정규칙 검색
    elif target == 'admrul':
        for item in root.findall('.//admrul'):
            admrul_id = item.findtext('행정규칙일련번호', '')
            admrul_name = item.findtext('행정규칙명', '')
            admrul_type = item.findtext('행정규칙종류', '')
            promul_date = item.findtext('발령일자', '')
            enforce_date = item.findtext('시행일자', '')
            ministry = item.findtext('소관부처명', '')

            results.append({
                'id': admrul_id,
                'name': admrul_name,
                'type': admrul_type,
                'promul_date': promul_date,
                'enforce_date': enforce_date,
                'ministry': ministry,
            })

            print(f"📋 [{admrul_type}] {admrul_name}")
            print(f"   ID: {admrul_id}")
            print(f"   소관: {ministry}")
            print(f"   발령일: {promul_date} | 시행일: {enforce_date}")
            print(f"   링크: https://www.law.go.kr/행정규칙/{urllib.parse.quote(admrul_name)}")
            print()

    # 자치법규 검색
    elif target == 'ordin':
        for item in root.findall('.//law'):
            ordin_id = item.findtext('자치법규일련번호', '') or item.findtext('자치법규ID', '')
            ordin_name = item.findtext('자치법규명', '')
            ordin_type = item.findtext('자치법규종류', '')
            local_gov = item.findtext('지자체기관명', '')
            promul_date = item.findtext('공포일자', '')
            enforce_date = item.findtext('시행일자', '')

            results.append({
                'id': ordin_id,
                'name': ordin_name,
                'type': ordin_type,
                'local_gov': local_gov,
                'promul_date': promul_date,
                'enforce_date': enforce_date,
            })

            print(f"🏛️  [{ordin_type}] {ordin_name}")
            print(f"   ID: {ordin_id}")
            print(f"   지자체: {local_gov}")
            print(f"   공포일: {promul_date} | 시행일: {enforce_date}")
            print(f"   링크: https://www.law.go.kr/자치법규/{urllib.parse.quote(ordin_name)}")
            print()

    # 법령해석례 검색
    elif target == 'expc':
        for item in root.findall('.//expc'):
            expc_id = item.findtext('법령해석례일련번호', '')
            case_name = item.findtext('안건명', '')
            case_number = item.findtext('안건번호', '')
            request_org = item.findtext('질의기관명', '')
            response_org = item.findtext('회신기관명', '')
            response_date = item.findtext('회신일자', '')

            results.append({
                'id': expc_id,
                'name': case_name,
                'case_number': case_number,
                'request_org': request_org,
                'response_org': response_org,
                'response_date': response_date,
            })

            print(f"📝 {case_name}")
            print(f"   안건번호: {case_number}")
            print(f"   질의기관: {request_org} → 회신기관: {response_org}")
            print(f"   회신일: {response_date}")
            print()

    # 헌재결정례 검색
    elif target == 'detc':
        for item in root.findall('.//Detc'):
            detc_id = item.findtext('헌재결정례일련번호', '')
            case_name = item.findtext('사건명', '')
            case_number = item.findtext('사건번호', '')
            decision_date = item.findtext('종국일자', '')
            decision_type = item.findtext('결정유형', '')
            case_type = item.findtext('사건종류', '')

            results.append({
                'id': detc_id,
                'name': case_name,
                'case_number': case_number,
                'decision_date': decision_date,
                'decision_type': decision_type,
                'case_type': case_type,
            })

            print(f"⚖️  {case_name}")
            print(f"   사건번호: {case_number}")
            print(f"   종국일: {decision_date}")
            if decision_type:
                print(f"   결정유형: {decision_type}")
            print(f"   링크: https://www.law.go.kr/헌재결정례/({case_number.replace(' ', '')})")
            print()

    # 법령 검색 (기본)
    else:
        for item in root.findall('.//law'):
            law_id = item.findtext('법령ID', '')
            law_name = item.findtext('법령명한글', '') or item.findtext('법령명', '')
            promul_date = item.findtext('공포일자', '')
            enforce_date = item.findtext('시행일자', '')
            ministry = item.findtext('소관부처명', '')
            law_type = item.findtext('법령구분명', '')

            results.append({
                'id': law_id,
                'name': law_name,
                'promul_date': promul_date,
                'enforce_date': enforce_date,
                'ministry': ministry,
                'type': law_type,
            })

            print(f"📜 {law_name}")
            print(f"   ID: {law_id}")
            print(f"   구분: {law_type} | 소관: {ministry}")
            print(f"   공포일: {promul_date} | 시행일: {enforce_date}")
            print(f"   링크: https://www.law.go.kr/법령/{urllib.parse.quote(law_name)}")
            print()

    return results


def search_cases(query: str, court: str = None, from_date: str = None, display: int = 20, page: int = 1):
    """
    판례 전용 검색

    Args:
        query: 검색어
        court: 법원 필터 (대법원, 고등, 지방 등)
        from_date: 검색 시작일 (YYYYMMDD)
        display: 결과 개수
        page: 페이지 번호
    """
    oc = load_config()

    params = {
        'OC': oc,
        'target': 'prec',
        'type': 'XML',
        'query': query,
        'display': display,
        'page': page,
    }

    # 날짜 필터 (선고일 기준)
    if from_date:
        params['sort'] = 'date'

    root = api_request('lawSearch.do', params)

    total = root.findtext('.//totalCnt', '0')
    print(f"\n=== 판례 검색 결과: '{query}' (총 {total}건) ===\n")

    results = []
    for item in root.findall('.//prec'):
        case_id = item.findtext('판례일련번호', '')
        case_name = item.findtext('사건명', '')
        case_number = item.findtext('사건번호', '')
        court_name = item.findtext('법원명', '')
        judge_date = item.findtext('선고일자', '')
        case_type = item.findtext('사건종류명', '')
        judgment_type = item.findtext('판결유형', '')

        # 법원 필터링
        if court and court not in court_name:
            continue

        # 날짜 필터링
        if from_date and judge_date and judge_date < from_date:
            continue

        results.append({
            'id': case_id,
            'name': case_name,
            'case_number': case_number,
            'court': court_name,
            'judge_date': judge_date,
            'type': case_type,
            'judgment_type': judgment_type,
        })

        # 판례 인용 형식으로 출력
        formatted_date = format_court_date(judge_date) if judge_date else ''
        print(f"⚖️  {court_name} {formatted_date} 선고 {case_number} 판결")
        print(f"   사건명: {case_name}")
        print(f"   사건종류: {case_type}")
        print(f"   링크: https://www.law.go.kr/판례/({case_number.replace(' ', '')})")
        print()

    print(f"총 {len(results)}건")
    return results


def format_court_date(date_str: str) -> str:
    """선고일자 포맷팅 (20230112 → 2023. 1. 12.)"""
    if len(date_str) == 8:
        year = date_str[:4]
        month = str(int(date_str[4:6]))
        day = str(int(date_str[6:8]))
        return f"{year}. {month}. {day}."
    return date_str


def find_cached_law(law_id: str = None, law_name: str = None) -> Path | None:
    """
    캐시된 법령 파일 찾기

    Args:
        law_id: 법령 ID
        law_name: 법령명

    Returns:
        캐시된 파일 경로 또는 None
    """
    if not DATA_RAW_DIR.exists():
        return None

    for filepath in DATA_RAW_DIR.glob("*.xml"):
        if law_id and law_id in filepath.name:
            return filepath
        if law_name:
            safe_name = "".join(c for c in law_name if c.isalnum() or c in (' ', '_', '-')).strip()
            if safe_name in filepath.name:
                return filepath
    return None


def fetch_law_by_id(law_id: str, save: bool = True, force: bool = False, target: str = "law"):
    """
    법령/행정규칙 등 ID로 본문 조회

    Args:
        law_id: 법령/행정규칙 일련번호
        save: 파일로 저장 여부
        force: 캐시 무시하고 강제 다운로드
        target: 검색 대상 (law, admrul, prec, ordin, expc, detc)
    """
    # 캐시 확인 (법령만)
    if not force and target == "law":
        cached = find_cached_law(law_id=law_id)
        if cached:
            print(f"\n✅ 캐시된 파일 사용: {cached}")
            tree = ET.parse(cached)
            root = tree.getroot()
            law_name = root.findtext('.//법령명_한글', '') or root.findtext('.//법령명', '')
            promul_date = root.findtext('.//공포일자', '')
            enforce_date = root.findtext('.//시행일자', '')
            print(f"=== {law_name} ===")
            print(f"공포일: {promul_date} | 시행일: {enforce_date}")
            print(f"(강제 다운로드: --force 옵션 사용)")
            return root

    oc = load_config()

    # 자치법규는 MST 파라미터 사용 (다른 타입은 ID)
    params = {
        'OC': oc,
        'target': target,
        'type': 'XML',
    }
    if target == 'ordin':
        params['MST'] = law_id
    else:
        params['ID'] = law_id

    root = api_request('lawService.do', params)

    # target 타입에 따라 다른 필드 추출 및 저장
    if target == 'admrul':
        # 행정규칙
        item_name = root.findtext('.//행정규칙명', '') or root.findtext('.//행정규칙명한글', '')
        promul_date = root.findtext('.//발령일자', '')
        enforce_date = root.findtext('.//시행일자', '')
        ministry = root.findtext('.//소관부처', '') or root.findtext('.//소관부처명', '')
        admrul_type = root.findtext('.//행정규칙종류', '')

        print(f"\n=== [{admrul_type}] {item_name} ===")
        print(f"소관: {ministry}")
        print(f"발령일: {promul_date} | 시행일: {enforce_date}")

        if save:
            safe_name = "".join(c for c in item_name if c.isalnum() or c in (' ', '_', '-')).strip()
            filename = f"{safe_name}_{law_id}.xml"
            filepath = DATA_RAW_DIR / "admrul" / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            tree = ET.ElementTree(root)
            tree.write(filepath, encoding='utf-8', xml_declaration=True)
            print(f"\n저장됨: {filepath}")

    elif target == 'ordin':
        # 자치법규
        item_name = root.findtext('.//자치법규명', '')
        promul_date = root.findtext('.//공포일자', '')
        enforce_date = root.findtext('.//시행일자', '')
        local_gov = root.findtext('.//지자체기관명', '')
        ordin_type = root.findtext('.//자치법규종류', '')

        # 자치법규종류 코드를 한글로 변환
        ordin_type_map = {'C0001': '조례', 'C0002': '규칙'}
        ordin_type_name = ordin_type_map.get(ordin_type, ordin_type)

        print(f"\n=== [{ordin_type_name}] {item_name} ===")
        print(f"지자체: {local_gov}")
        print(f"공포일: {promul_date} | 시행일: {enforce_date}")

        if save:
            safe_name = "".join(c for c in item_name if c.isalnum() or c in (' ', '_', '-')).strip()
            filename = f"{safe_name}_{law_id}.xml"
            filepath = DATA_RAW_DIR / "ordin" / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            tree = ET.ElementTree(root)
            tree.write(filepath, encoding='utf-8', xml_declaration=True)
            print(f"\n저장됨: {filepath}")

    elif target == 'expc':
        # 법령해석례
        item_name = root.findtext('.//안건명', '')
        case_number = root.findtext('.//안건번호', '')
        response_date = root.findtext('.//해석일자', '')
        request_org = root.findtext('.//질의기관명', '')
        response_org = root.findtext('.//해석기관명', '')

        print(f"\n=== 법령해석례: {item_name} ===")
        print(f"안건번호: {case_number}")
        print(f"질의: {request_org} → 해석: {response_org}")
        print(f"해석일: {response_date}")

        # 질의요지/회답 출력
        question = root.findtext('.//질의요지', '')
        answer = root.findtext('.//회답', '')
        if question:
            print(f"\n【질의요지】")
            print(question[:500] + "..." if len(question) > 500 else question)
        if answer:
            print(f"\n【회답】")
            print(answer[:500] + "..." if len(answer) > 500 else answer)

        if save:
            safe_name = "".join(c for c in case_number if c.isalnum() or c in (' ', '_', '-')).strip()
            filename = f"{safe_name}_{law_id}.xml"
            filepath = DATA_RAW_DIR / "expc" / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            tree = ET.ElementTree(root)
            tree.write(filepath, encoding='utf-8', xml_declaration=True)
            print(f"\n저장됨: {filepath}")

    elif target == 'detc':
        # 헌재결정례
        item_name = root.findtext('.//사건명', '')
        case_number = root.findtext('.//사건번호', '')
        decision_date = root.findtext('.//종국일자', '')
        case_type = root.findtext('.//사건종류명', '')

        print(f"\n=== 헌재결정례: {item_name} ===")
        print(f"사건번호: {case_number}")
        print(f"사건종류: {case_type}")
        print(f"종국일: {decision_date}")

        # 판시사항/결정요지 출력
        points = root.findtext('.//판시사항', '')
        summary = root.findtext('.//결정요지', '')
        if points:
            print(f"\n【판시사항】")
            points_clean = re.sub(r'<[^>]+>', '', points)
            print(points_clean[:500] + "..." if len(points_clean) > 500 else points_clean)
        if summary:
            print(f"\n【결정요지】")
            summary_clean = re.sub(r'<[^>]+>', '', summary)
            print(summary_clean[:500] + "..." if len(summary_clean) > 500 else summary_clean)

        if save:
            safe_name = "".join(c for c in case_number if c.isalnum() or c in (' ', '_', '-')).strip()
            filename = f"{safe_name}_{law_id}.xml"
            filepath = DATA_RAW_DIR / "detc" / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            tree = ET.ElementTree(root)
            tree.write(filepath, encoding='utf-8', xml_declaration=True)
            print(f"\n저장됨: {filepath}")

    elif target == 'prec':
        # 판례 (fetch_case_by_id와 동일한 로직)
        item_name = root.findtext('.//사건명', '')
        case_number = root.findtext('.//사건번호', '')
        court_name = root.findtext('.//법원명', '')
        judge_date = root.findtext('.//선고일자', '')

        print(f"\n=== {item_name} ===")
        print(f"사건번호: {case_number}")
        print(f"법원: {court_name} | 선고일: {format_court_date(judge_date)}")

        # 판시사항/판결요지 출력
        points = root.findtext('.//판시사항', '')
        summary = root.findtext('.//판결요지', '')
        if points:
            print(f"\n【판시사항】")
            points_clean = re.sub(r'<br\s*/?>', '\n', points)
            points_clean = re.sub(r'<[^>]+>', '', points_clean)
            print(points_clean[:500] + "..." if len(points_clean) > 500 else points_clean)
        if summary:
            print(f"\n【판결요지】")
            summary_clean = re.sub(r'<br\s*/?>', '\n', summary)
            summary_clean = re.sub(r'<[^>]+>', '', summary_clean)
            print(summary_clean[:500] + "..." if len(summary_clean) > 500 else summary_clean)

        if save:
            safe_name = "".join(c for c in case_number if c.isalnum() or c in (' ', '_', '-')).strip()
            filename = f"{safe_name}_{law_id}.xml"
            filepath = DATA_RAW_DIR / "prec" / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            tree = ET.ElementTree(root)
            tree.write(filepath, encoding='utf-8', xml_declaration=True)
            print(f"\n저장됨: {filepath}")

    else:
        # 법령 (기본)
        item_name = root.findtext('.//법령명_한글', '') or root.findtext('.//법령명', '')
        promul_date = root.findtext('.//공포일자', '')
        enforce_date = root.findtext('.//시행일자', '')

        print(f"\n=== {item_name} ===")
        print(f"공포일: {promul_date} | 시행일: {enforce_date}")

        if save:
            safe_name = "".join(c for c in item_name if c.isalnum() or c in (' ', '_', '-')).strip()
            filename = f"{safe_name}_{law_id}.xml"
            filepath = DATA_RAW_DIR / filename
            DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
            tree = ET.ElementTree(root)
            tree.write(filepath, encoding='utf-8', xml_declaration=True)
            print(f"\n저장됨: {filepath}")

    return root


def fetch_law_by_name(name: str, with_decree: bool = False, force: bool = False):
    """법령명으로 검색 후 첫 번째 결과 다운로드"""
    # 캐시 확인
    if not force:
        cached = find_cached_law(law_name=name)
        if cached:
            print(f"\n✅ 캐시된 파일 사용: {cached}")
            tree = ET.parse(cached)
            root = tree.getroot()
            law_name = root.findtext('.//법령명_한글', '') or root.findtext('.//법령명', '')
            promul_date = root.findtext('.//공포일자', '')
            enforce_date = root.findtext('.//시행일자', '')
            print(f"=== {law_name} ===")
            print(f"공포일: {promul_date} | 시행일: {enforce_date}")
            print(f"(강제 다운로드: --force 옵션 사용)")
            return root

    # 주요 법령인 경우 설정 파일에서 ID 직접 조회
    major_law_id = get_major_law_id(name)
    if major_law_id:
        print(f"📌 '{name}'은 주요 법령입니다. (ID: {major_law_id})")
        return fetch_law_by_id(major_law_id, force=True)

    results = search_laws(name, display=5)

    if not results:
        print(f"Error: '{name}' 검색 결과가 없습니다.", file=sys.stderr)
        sys.exit(1)

    # 정확히 일치하는 법령 찾기
    exact_match = None
    for r in results:
        if r['name'] == name or r['name'].replace(' ', '') == name.replace(' ', ''):
            exact_match = r
            break

    target = exact_match or results[0]
    law_id = target['id']
    print(f"\n'{target['name']}' 다운로드 중...")
    root = fetch_law_by_id(law_id, force=True)  # 이미 캐시 확인했으므로 force=True

    # 시행령도 함께 다운로드
    if with_decree:
        decree_name = f"{name}시행령"
        print(f"\n'{decree_name}' 검색 중...")
        decree_results = search_laws(decree_name, display=3)

        if decree_results:
            for dr in decree_results:
                if '시행령' in dr['name']:
                    print(f"'{dr['name']}' 다운로드 중...")
                    fetch_law_by_id(dr['id'])
                    break

        # 시행규칙도 검색
        rule_name = f"{name}시행규칙"
        print(f"\n'{rule_name}' 검색 중...")
        rule_results = search_laws(rule_name, display=3)

        if rule_results:
            for rr in rule_results:
                if '시행규칙' in rr['name']:
                    print(f"'{rr['name']}' 다운로드 중...")
                    fetch_law_by_id(rr['id'])
                    break

    return root


def get_recent_laws(days: int = 30, from_date: str = None, to_date: str = None, target: str = "law", date_type: str = "ef"):
    """
    최근 개정 법령 조회

    Args:
        days: 최근 N일
        from_date: 시작일 (YYYYMMDD)
        to_date: 종료일 (YYYYMMDD)
        target: 검색 대상
        date_type: 날짜 기준 (ef: 시행일, anc: 공포일)
    """
    oc = load_config()

    # 날짜 범위 계산
    if from_date and to_date:
        date_range = f"{from_date}~{to_date}"
    else:
        end = datetime.now()
        start = end - timedelta(days=days)
        from_date = start.strftime('%Y%m%d')
        to_date = end.strftime('%Y%m%d')
        date_range = f"{from_date}~{to_date}"

    params = {
        'OC': oc,
        'target': target,
        'type': 'XML',
        'display': 100,
        'sort': 'efdes',  # 시행일자 내림차순
    }

    # 날짜 범위 파라미터 추가 (efYd: 시행일자, ancYd: 공포일자)
    if date_type == "anc":
        params['ancYd'] = date_range
        params['sort'] = 'ddes'  # 공포일자 내림차순
    else:
        params['efYd'] = date_range

    root = api_request('lawSearch.do', params)

    total = root.findtext('.//totalCnt', '0')
    date_type_name = "공포일" if date_type == "anc" else "시행일"
    print(f"\n=== 최근 법령 목록 ({date_type_name} 기준: {date_range}) - 총 {total}건 ===\n")

    results = []
    for item in root.findall('.//law'):
        law_id = item.findtext('법령ID', '')
        law_name = item.findtext('법령명한글', '') or item.findtext('법령명', '')
        promul_date = item.findtext('공포일자', '')
        enforce_date = item.findtext('시행일자', '')
        ministry = item.findtext('소관부처명', '')
        revision_type = item.findtext('제개정구분명', '')

        results.append({
            'id': law_id,
            'name': law_name,
            'promul_date': promul_date,
            'enforce_date': enforce_date,
            'ministry': ministry,
            'revision_type': revision_type,
        })

        revision_emoji = "🆕" if revision_type == "제정" else "📝"
        print(f"{revision_emoji} [{revision_type}] {law_name}")
        print(f"   공포일: {promul_date} | 시행일: {enforce_date}")
        print(f"   소관: {ministry}")
        print()

    print(f"표시: {len(results)}건 / 전체: {total}건")
    return results


def search_exact_law(name: str, with_admrul: bool = False):
    """
    정확한 법령명으로 검색 (클라이언트측 필터링)

    Args:
        name: 정확한 법령명 (예: "상법", "민법")
        with_admrul: 관련 행정규칙도 함께 검색 여부

    Note:
        API는 부분 일치 검색만 지원하므로, 결과에서 정확히 일치하는 것만 필터링
    """
    # 주요 법령인 경우 설정 파일에서 ID 직접 활용
    major_law_id = get_major_law_id(name)
    if major_law_id:
        print(f"\n💡 '{name}'은 주요 법령입니다. 직접 조회합니다...")
        print(f"   → python scripts/fetch_law.py fetch --id {major_law_id}\n")

    oc = load_config()

    # 충분한 결과를 가져와서 필터링
    params = {
        'OC': oc,
        'target': 'law',
        'type': 'XML',
        'query': name,
        'display': 100,
    }

    root = api_request('lawSearch.do', params)

    print(f"\n=== 법령 정확 검색: '{name}' ===\n")

    results = []
    exact_matches = []
    related_matches = []

    for item in root.findall('.//law'):
        law_id = item.findtext('법령ID', '')
        law_name = item.findtext('법령명한글', '') or item.findtext('법령명', '')
        promul_date = item.findtext('공포일자', '')
        enforce_date = item.findtext('시행일자', '')
        ministry = item.findtext('소관부처명', '')
        law_type = item.findtext('법령구분명', '')

        result = {
            'id': law_id,
            'name': law_name,
            'promul_date': promul_date,
            'enforce_date': enforce_date,
            'ministry': ministry,
            'type': law_type,
        }

        # 정확히 일치하는지 확인
        clean_name = name.replace(' ', '')
        clean_law_name = law_name.replace(' ', '')

        if clean_law_name == clean_name:
            exact_matches.append(result)
        elif clean_law_name.startswith(clean_name) and ('시행령' in law_name or '시행규칙' in law_name):
            related_matches.append(result)

    # 정확히 일치하는 법령 출력
    if exact_matches:
        print("📌 정확히 일치하는 법령:\n")
        for r in exact_matches:
            print(f"📜 {r['name']}")
            print(f"   ID: {r['id']}")
            print(f"   구분: {r['type']} | 소관: {r['ministry']}")
            print(f"   공포일: {r['promul_date']} | 시행일: {r['enforce_date']}")
            print(f"   링크: https://www.law.go.kr/법령/{urllib.parse.quote(r['name'])}")
            print()
        results.extend(exact_matches)
    else:
        print(f"⚠️  '{name}'과 정확히 일치하는 법령이 없습니다.\n")

    # 관련 법령 (시행령, 시행규칙) 출력
    if related_matches:
        print("📎 관련 법령 (시행령/시행규칙):\n")
        for r in related_matches:
            print(f"📜 {r['name']}")
            print(f"   ID: {r['id']}")
            print(f"   구분: {r['type']} | 소관: {r['ministry']}")
            print(f"   공포일: {r['promul_date']} | 시행일: {r['enforce_date']}")
            print()
        results.extend(related_matches)

    if not results:
        print(f"💡 힌트: '{name}'을 포함하는 법령을 검색하려면:")
        print(f"   python scripts/fetch_law.py search \"{name}\"")

    # 관련 행정규칙 검색
    if with_admrul:
        print(f"\n{'='*60}")
        print(f"📋 관련 행정규칙 (고시/훈령/예규) 검색 중...")
        print(f"{'='*60}")
        search_related_admin_rules(name)

    return results


def search_related_admin_rules(law_name: str, display: int = 10):
    """
    법령명과 관련된 행정규칙 검색

    Args:
        law_name: 법령명 (예: "개인정보보호법", "근로기준법")
        display: 표시할 결과 수
    """
    oc = load_config()

    # 다양한 검색 패턴 시도
    search_terms = [
        law_name,  # 법령명 그대로
        f"{law_name} 시행",  # 시행 관련
        f"{law_name} 기준",  # 기준 관련
    ]

    all_results = []
    seen_ids = set()

    for term in search_terms:
        params = {
            'OC': oc,
            'target': 'admrul',
            'type': 'XML',
            'query': term,
            'display': display,
        }

        try:
            root = api_request('lawSearch.do', params)

            for item in root.findall('.//admrul'):
                admrul_id = item.findtext('행정규칙일련번호', '')
                if admrul_id in seen_ids:
                    continue
                seen_ids.add(admrul_id)

                admrul_name = item.findtext('행정규칙명', '')
                admrul_type = item.findtext('행정규칙종류', '')
                promul_date = item.findtext('발령일자', '')
                enforce_date = item.findtext('시행일자', '')
                ministry = item.findtext('소관부처명', '')

                all_results.append({
                    'id': admrul_id,
                    'name': admrul_name,
                    'type': admrul_type,
                    'promul_date': promul_date,
                    'enforce_date': enforce_date,
                    'ministry': ministry,
                })
        except (urllib.error.HTTPError, urllib.error.URLError, ET.ParseError):
            # API 오류 시 다음 검색어로 계속
            continue

    if all_results:
        print(f"\n=== '{law_name}' 관련 행정규칙 (총 {len(all_results)}건) ===\n")
        print("⚠️  실무 팁: 법률은 큰 틀만 정합니다. 구체적인 기준/절차/서식은")
        print("   아래 행정규칙(고시/훈령/예규)에서 확인하세요!\n")

        for r in all_results[:display]:
            print(f"📋 [{r['type']}] {r['name']}")
            print(f"   ID: {r['id']}")
            print(f"   소관: {r['ministry']}")
            print(f"   발령일: {r['promul_date']} | 시행일: {r['enforce_date']}")
            print(f"   링크: https://www.law.go.kr/행정규칙/{urllib.parse.quote(r['name'])}")
            print()
    else:
        print(f"\n'{law_name}' 관련 행정규칙을 찾지 못했습니다.")
        print(f"💡 직접 검색: python scripts/fetch_law.py search \"{law_name}\" --type admrul")

    return all_results


def fetch_case_by_id(case_id: str, save: bool = True):
    """
    판례 ID로 본문 조회

    Args:
        case_id: 판례일련번호
        save: 파일로 저장 여부
    """
    oc = load_config()

    params = {
        'OC': oc,
        'target': 'prec',
        'type': 'XML',
        'ID': case_id,
    }

    root = api_request('lawService.do', params)

    # 기본 정보 추출
    case_name = root.findtext('.//사건명', '')
    case_number = root.findtext('.//사건번호', '')
    court_name = root.findtext('.//법원명', '')
    judge_date = root.findtext('.//선고일자', '')

    print(f"\n=== {case_name} ===")
    print(f"사건번호: {case_number}")
    print(f"법원: {court_name} | 선고일: {format_court_date(judge_date)}")

    # 판시사항
    points = root.findtext('.//판시사항', '')
    if points:
        print(f"\n【판시사항】")
        points_clean = re.sub(r'<br\s*/?>', '\n', points)
        points_clean = re.sub(r'<[^>]+>', '', points_clean)
        print(points_clean.strip())

    # 판결요지
    summary = root.findtext('.//판결요지', '')
    if summary:
        print(f"\n【판결요지】")
        summary_clean = re.sub(r'<br\s*/?>', '\n', summary)
        summary_clean = re.sub(r'<[^>]+>', '', summary_clean)
        print(summary_clean.strip())

    if save:
        # 파일명에서 특수문자 제거
        safe_name = "".join(c for c in case_number if c.isalnum() or c in (' ', '_', '-')).strip()
        filename = f"{safe_name}_{case_id}.xml"
        filepath = DATA_RAW_DIR / "prec" / filename

        # XML 저장
        filepath.parent.mkdir(parents=True, exist_ok=True)
        tree = ET.ElementTree(root)
        tree.write(filepath, encoding='utf-8', xml_declaration=True)
        print(f"\n저장됨: {filepath}")

    return root


def fetch_case_by_number(case_number: str):
    """사건번호로 검색 후 첫 번째 결과 다운로드"""
    results = search_cases(case_number, display=5)

    if not results:
        print(f"Error: '{case_number}' 검색 결과가 없습니다.", file=sys.stderr)
        sys.exit(1)

    # 정확히 일치하는 판례 찾기
    exact_match = None
    clean_number = case_number.replace(' ', '')
    for r in results:
        if r['case_number'].replace(' ', '') == clean_number:
            exact_match = r
            break

    target = exact_match or results[0]
    case_id = target['id']
    print(f"\n'{target['case_number']}' 다운로드 중...")
    return fetch_case_by_id(case_id)


def main():
    parser = argparse.ArgumentParser(description='Korean Law Fetcher')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # search 명령
    search_parser = subparsers.add_parser('search', help='법령/판례 검색')
    search_parser.add_argument('query', help='검색어')
    search_parser.add_argument('--type', default='law',
                               choices=['law', 'prec', 'ordin', 'admrul', 'expc', 'detc'],
                               help='검색 대상 (law: 법령, prec: 판례, ordin: 자치법규, admrul: 행정규칙, expc: 법령해석례, detc: 헌재결정례)')
    search_parser.add_argument('--display', type=int, default=20, help='결과 개수')
    search_parser.add_argument('--page', type=int, default=1, help='페이지 번호')
    search_parser.add_argument('--sort', choices=['date', 'name'], help='정렬 기준 (date: 날짜순, name: 이름순)')

    # cases 명령 (판례 전용)
    cases_parser = subparsers.add_parser('cases', help='판례 검색')
    cases_parser.add_argument('query', help='검색어')
    cases_parser.add_argument('--court', help='법원 필터 (대법원, 고등, 지방)')
    cases_parser.add_argument('--from', dest='from_date', help='검색 시작일 (YYYYMMDD)')
    cases_parser.add_argument('--display', type=int, default=20, help='결과 개수')
    cases_parser.add_argument('--page', type=int, default=1, help='페이지 번호')

    # exact 명령 (정확한 법령명 검색)
    exact_parser = subparsers.add_parser('exact', help='정확한 법령명 검색 (예: 상법, 민법)')
    exact_parser.add_argument('name', help='정확한 법령명')
    exact_parser.add_argument('--with-admrul', action='store_true',
                              help='관련 행정규칙(고시/훈령/예규)도 함께 검색')

    # fetch 명령
    fetch_parser = subparsers.add_parser('fetch', help='법령/판례/행정규칙 다운로드')
    fetch_parser.add_argument('--id', help='법령/판례/행정규칙 ID')
    fetch_parser.add_argument('--name', help='법령명')
    fetch_parser.add_argument('--case', help='판례 사건번호 (예: 2022다12345)')
    fetch_parser.add_argument('--type', default='law',
                              choices=['law', 'admrul', 'prec', 'ordin', 'expc', 'detc'],
                              help='다운로드 대상 (law: 법령, admrul: 행정규칙, prec: 판례 등)')
    fetch_parser.add_argument('--with-decree', action='store_true',
                              help='시행령/시행규칙도 함께 다운로드')
    fetch_parser.add_argument('--force', action='store_true',
                              help='캐시 무시하고 강제 다운로드')

    # recent 명령
    recent_parser = subparsers.add_parser('recent', help='최근 개정 법령')
    recent_parser.add_argument('--days', type=int, default=30, help='최근 N일')
    recent_parser.add_argument('--from', dest='from_date', help='시작일 (YYYYMMDD)')
    recent_parser.add_argument('--to', dest='to_date', help='종료일 (YYYYMMDD)')
    recent_parser.add_argument('--date-type', choices=['ef', 'anc'], default='ef',
                               help='날짜 기준 (ef: 시행일, anc: 공포일)')

    args = parser.parse_args()

    if args.command == 'search':
        search_laws(args.query, args.type, args.display, args.page, args.sort)
    elif args.command == 'exact':
        search_exact_law(args.name, with_admrul=args.with_admrul)
    elif args.command == 'cases':
        search_cases(args.query, args.court, args.from_date, args.display, args.page)
    elif args.command == 'fetch':
        if args.case:
            fetch_case_by_number(args.case)
        elif args.id:
            fetch_law_by_id(args.id, force=args.force, target=args.type)
        elif args.name:
            fetch_law_by_name(args.name, args.with_decree, args.force)
        else:
            print("Error: --id, --name, 또는 --case 중 하나를 지정하세요.", file=sys.stderr)
            sys.exit(1)
    elif args.command == 'recent':
        get_recent_laws(args.days, args.from_date, args.to_date, date_type=args.date_type)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
