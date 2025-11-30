#!/usr/bin/env python3
"""
Korean Policy Stance Fetcher - 정부 정책 집행 동향 수집

정부 부처 보도자료, 행정해석, 입법예고 등을 수집하여
정책 집행 스탠스를 파악할 수 있도록 지원합니다.

Usage:
    python fetch_policy.py rss [부처코드] [--keyword 키워드]
    python fetch_policy.py interpret "검색어" [--display 20]
    python fetch_policy.py legislative [--status ongoing|completed] [--days 30]
    python fetch_policy.py summary [--days 7]
"""

import argparse
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

import yaml

# 프록시 유틸리티 (해외 접근 지원)
try:
    from proxy_utils import fetch_with_proxy, is_overseas, get_geo_status
    HAS_PROXY_UTILS = True
except ImportError:
    HAS_PROXY_UTILS = False

# 스크립트 위치 기준으로 경로 설정
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_PATH = SKILL_DIR / "config" / "settings.yaml"
DATA_POLICY_DIR = SKILL_DIR / "data" / "policy"

# 환경변수 이름
ENV_OC_CODE = "BEOPSUNY_OC_CODE"
ENV_DATA_GO_KR_KEY = "BEOPSUNY_DATA_GO_KR_KEY"

# 정부 부처 RSS 피드 URL (정책브리핑 korea.kr)
RSS_FEEDS = {
    "ftc": {
        "name": "공정거래위원회",
        "url": "https://korea.kr/rss/dept_ftc.xml",
        "keywords": ["공정거래", "하도급", "가맹", "과징금", "시정명령", "불공정거래"],
    },
    "moel": {
        "name": "고용노동부",
        "url": "https://korea.kr/rss/dept_moel.xml",
        "keywords": ["근로기준", "산업안전", "임금", "해고", "노동", "고용"],
    },
    "fsc": {
        "name": "금융위원회",
        "url": "https://korea.kr/rss/dept_fsc.xml",
        "keywords": ["금융", "제재", "자본시장", "금융소비자", "과징금"],
    },
    "pipc": {
        "name": "개인정보보호위원회",
        "url": "https://korea.kr/rss/dept_pipc.xml",
        "keywords": ["개인정보", "과징금", "제재", "시정조치"],
    },
    "moleg": {
        "name": "법제처",
        "url": "https://korea.kr/rss/dept_moleg.xml",
        "keywords": ["법령", "입법", "법제"],
    },
}

# API 엔드포인트
API_ENDPOINTS = {
    "moel_interpret": "http://www.law.go.kr/DRF/lawSearch.do",  # 고용노동부 행정해석
    "legislative": "https://opinion.lawmaking.go.kr/rest/ogLmPp",  # 입법예고
}

# 캐시
_config_cache = None


def _load_config_file():
    """설정 파일 로드 (캐싱)"""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            _config_cache = yaml.safe_load(f) or {}
    else:
        _config_cache = {}

    return _config_cache


def get_oc_code() -> str:
    """OC 코드 로드 (환경변수 > 설정파일)

    Raises:
        ValueError: OC 코드를 찾을 수 없는 경우
    """
    oc_code = os.environ.get(ENV_OC_CODE)
    if oc_code:
        return oc_code

    config = _load_config_file()
    oc_code = config.get("oc_code", "")

    if not oc_code:
        raise ValueError(
            f"OC code not found. "
            f"Set environment variable {ENV_OC_CODE} or configure in {CONFIG_PATH}"
        )

    return oc_code


def ensure_data_dir():
    """데이터 디렉토리 생성"""
    DATA_POLICY_DIR.mkdir(parents=True, exist_ok=True)


def fetch_url(url: str, timeout: int = 30) -> str:
    """URL에서 데이터 가져오기 (해외 실행 시 자동 프록시)

    Args:
        url: 요청할 URL
        timeout: 타임아웃 (초)

    Returns:
        응답 본문 (UTF-8 디코딩)

    Raises:
        RuntimeError: 네트워크 오류 발생 시
    """
    # 프록시 유틸리티 사용 가능하면 자동 프록시 처리
    if HAS_PROXY_UTILS:
        try:
            return fetch_with_proxy(url, timeout=timeout)
        except ValueError as e:
            # 프록시 미설정 시 경고 후 직접 시도
            if is_overseas():
                print(f"Warning: {e}", file=sys.stderr)
                print("Attempting direct connection...", file=sys.stderr)

    # 직접 접근 (국내 또는 프록시 미설정)
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; Beopsuny/1.0; +https://github.com/sungjunlee/beopsuny-template)"
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP error {e.code}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL error: {e.reason}") from e
    except socket.timeout:
        raise RuntimeError(f"Request timeout after {timeout}s") from None
    except Exception as e:
        raise RuntimeError(f"Unexpected error fetching URL: {e}") from e


# ============================================================
# RSS 피드 수집
# ============================================================


def fetch_rss(
    dept_code: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, str]]:
    """RSS 피드에서 보도자료 수집

    Args:
        dept_code: 부처 코드 (ftc, moel, fsc, pipc, moleg). None이면 전체 조회
        keyword: 필터링 키워드
        limit: 부처당 최대 건수

    Returns:
        보도자료 목록

    Raises:
        ImportError: feedparser 미설치 시
        ValueError: 잘못된 부처 코드
    """
    if not HAS_FEEDPARSER:
        raise ImportError(
            "feedparser 라이브러리가 필요합니다. 설치: pip install feedparser"
        )

    # 부처 코드 검증
    if dept_code:
        if dept_code not in RSS_FEEDS:
            raise ValueError(
                f"알 수 없는 부처 코드: {dept_code}. "
                f"가능한 코드: {', '.join(RSS_FEEDS.keys())}"
            )
        feeds_to_check = {dept_code: RSS_FEEDS[dept_code]}
    else:
        feeds_to_check = RSS_FEEDS

    results = []

    for code, feed_info in feeds_to_check.items():
        try:
            feed = feedparser.parse(feed_info["url"])

            # feedparser bozo 오류 체크 (파싱 경고)
            if hasattr(feed, "bozo") and feed.bozo:
                print(
                    f"Warning: {feed_info['name']} RSS 파싱 경고: {feed.bozo_exception}",
                    file=sys.stderr,
                )

            if not feed.entries:
                print(
                    f"Warning: {feed_info['name']} RSS에 항목이 없습니다.",
                    file=sys.stderr,
                )
                continue

            for entry in feed.entries[:limit]:
                # 필수 필드 검증
                title = entry.get("title", "")
                if not title:
                    continue

                # 키워드 필터링
                if keyword:
                    title_lower = title.lower()
                    summary_lower = entry.get("summary", "").lower()
                    if keyword.lower() not in title_lower and keyword.lower() not in summary_lower:
                        continue

                results.append({
                    "dept": feed_info["name"],
                    "dept_code": code,
                    "title": title,
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "summary": entry.get("summary", "")[:200] if entry.get("summary") else "",
                })
        except Exception as e:
            print(f"Warning: {feed_info['name']} RSS 수집 실패: {e}", file=sys.stderr)

    return results


def cmd_rss(args):
    """RSS 보도자료 수집 명령"""
    try:
        results = fetch_rss(args.dept, args.keyword, args.limit)
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if not results:
        print("검색 결과가 없습니다.")
        return

    print(f"\n📰 보도자료 ({len(results)}건)")
    print("=" * 60)

    for item in results:
        print(f"\n[{item['dept']}] {item['title']}")
        print(f"  📅 {item['published']}")
        print(f"  🔗 {item['link']}")
        if item["summary"]:
            print(f"  📝 {item['summary'][:100]}...")


# ============================================================
# 법령해석례 검색 (법제처)
# ============================================================


# XML 필드 매핑 (여러 API 응답 형식 지원)
INTERPRET_FIELD_MAPPINGS = {
    "seq": ["법령해석일련번호", "expcSeq"],
    "title": ["안건명", "expcNm"],
    "case_no": ["안건번호", "expcNo"],
    "query_org": ["질의기관명", "qryInsttNm"],
    "interpret_org": ["해석기관명", "anwInsttNm"],
    "interpret_date": ["해석일자", "anwYd"],
}


def _get_xml_field(item: ET.Element, field_key: str) -> str:
    """XML 아이템에서 여러 가능한 필드명 중 첫 번째 값 반환"""
    for field_name in INTERPRET_FIELD_MAPPINGS.get(field_key, []):
        value = item.findtext(field_name, "")
        if value:
            return value
    return ""


def _is_html_error_response(content: str) -> bool:
    """응답이 HTML 에러 페이지인지 확인"""
    stripped = content.strip()
    return (
        stripped.startswith("<!DOCTYPE")
        or stripped.startswith("<html")
        or stripped.startswith("<HTML")
    )


def search_legal_interpret(
    query: str,
    display: int = 20,
    page: int = 1,
    target: str = "expc",
) -> Dict[str, Any]:
    """법령해석례 검색

    Args:
        query: 검색어
        display: 표시 건수 (최대 100)
        page: 페이지 번호
        target: API 타겟 (expc: 일반, moelCgmExpc: 고용노동부)

    Returns:
        검색 결과 딕셔너리 (total, results, error 키 포함)
    """
    try:
        oc = get_oc_code()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return {"total": 0, "results": [], "error": "config_error"}

    params = {
        "OC": oc,
        "target": target,
        "type": "XML",
        "query": query,
        "display": display,
        "page": page,
    }

    url = f"{API_ENDPOINTS['moel_interpret']}?{urllib.parse.urlencode(params)}"

    try:
        content = fetch_url(url)

        # HTML 에러 페이지 감지 (인증 실패 등)
        if _is_html_error_response(content):
            print(f"Warning: API 인증 실패 (target={target})", file=sys.stderr)
            print(f"  - 법령해석례(expc)는 별도 API 권한이 필요할 수 있습니다.", file=sys.stderr)
            print(f"  - https://open.law.go.kr 에서 권한 확인 바랍니다.", file=sys.stderr)
            return {"total": 0, "results": [], "error": "auth_failed"}

        root = ET.fromstring(content)

        # XML 내부 에러 메시지 확인
        error_msg = root.findtext(".//errorMsg") or root.findtext(".//retMsg")
        if error_msg and ("인증" in error_msg or "401" in error_msg):
            print(f"Warning: API 인증 오류: {error_msg}", file=sys.stderr)
            return {"total": 0, "results": [], "error": "auth_failed"}

        results = []
        # expc와 moelCgmExpc 두 가지 태그 모두 지원
        for tag in ["expc", "moelCgmExpc"]:
            for item in root.findall(f".//{tag}"):
                results.append({
                    "seq": _get_xml_field(item, "seq"),
                    "title": _get_xml_field(item, "title"),
                    "case_no": _get_xml_field(item, "case_no"),
                    "query_org": _get_xml_field(item, "query_org"),
                    "interpret_org": _get_xml_field(item, "interpret_org"),
                    "interpret_date": _get_xml_field(item, "interpret_date"),
                })

        total = root.findtext(".//totalCnt", "0")
        return {"total": int(total), "results": results}

    except RuntimeError as e:
        print(f"Error: 네트워크 오류: {e}", file=sys.stderr)
        return {"total": 0, "results": [], "error": "network_error"}
    except ET.ParseError as e:
        print(f"Error: XML 파싱 실패: {e}", file=sys.stderr)
        return {"total": 0, "results": [], "error": "parse_error"}
    except Exception as e:
        print(f"Error: 법령해석 검색 실패: {e}", file=sys.stderr)
        return {"total": 0, "results": [], "error": str(e)}


def cmd_interpret(args):
    """법령해석례 검색 명령"""
    data = search_legal_interpret(args.query, args.display)

    if data.get("error") == "auth_failed":
        print(f"\n⚠️  법령해석례 API 접근 권한이 없습니다.")
        print(f"    https://open.law.go.kr 에서 권한 신청이 필요합니다.")
        print(f"\n💡 대안: 웹검색으로 법령해석 사례를 조회하세요:")
        print(f'   검색어: "{args.query} 법령해석" site:law.go.kr')
        return

    if data["total"] == 0:
        print(f"'{args.query}' 관련 법령해석례를 찾을 수 없습니다.")
        return

    print(f"\n📋 법령해석례 (총 {data['total']}건 중 {len(data['results'])}건)")
    print("=" * 60)

    for item in data["results"]:
        print(f"\n📌 {item['title']}")
        print(f"   안건번호: {item['case_no']}")
        if item['query_org']:
            print(f"   질의기관: {item['query_org']}")
        if item['interpret_org']:
            print(f"   해석기관: {item['interpret_org']}")
        print(f"   해석일자: {item['interpret_date']}")


# ============================================================
# 입법예고 검색
# ============================================================


def search_legislative(
    status: str = "ongoing",
    law_name: str = None,
    days: int = 30,
    display: int = 20,
):
    """입법예고 검색"""
    oc = get_oc_code()

    # 날짜 범위 계산
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    params = {
        "OC": oc,
        "diff": "0" if status == "ongoing" else "1",
        "stYdFmt": start_date.strftime("%Y.%m.%d."),
        "edYdFmt": end_date.strftime("%Y.%m.%d."),
    }

    if law_name:
        params["lsNm"] = law_name

    url = f"{API_ENDPOINTS['legislative']}.xml?{urllib.parse.urlencode(params)}"

    try:
        content = fetch_url(url)

        # 401 인증 오류 감지
        if "<retMsg>401</retMsg>" in content:
            return {"error": "auth_failed", "results": []}

        root = ET.fromstring(content)

        results = []
        # XML 구조에 따라 파싱 (실제 응답 구조에 맞게 조정 필요)
        for item in root.findall(".//ogLmPp"):
            results.append({
                "title": item.findtext("lsNm", ""),
                "ministry": item.findtext("cptOfiNm", ""),
                "notice_no": item.findtext("pntcNo", ""),
                "start_date": item.findtext("stYd", ""),
                "end_date": item.findtext("edYd", ""),
                "status": "진행중" if status == "ongoing" else "완료",
            })

        return {"results": results[:display]}

    except ET.ParseError:
        # XML 파싱 실패 시 빈 결과 반환
        print(f"Warning: 입법예고 XML 파싱 실패", file=sys.stderr)
        return {"error": "parse_error", "results": []}
    except Exception as e:
        print(f"Error: 입법예고 검색 실패: {e}", file=sys.stderr)
        return {"error": str(e), "results": []}


def cmd_legislative(args):
    """입법예고 검색 명령"""
    data = search_legislative(
        status=args.status,
        law_name=args.law_name,
        days=args.days,
        display=args.display,
    )

    if data.get("error") == "auth_failed":
        print(f"\n⚠️  입법예고 API 접근 권한이 없습니다.")
        print(f"    국민참여입법센터에서 별도 권한 신청이 필요합니다.")
        print(f"\n💡 대안: 웹사이트에서 직접 확인하세요:")
        print(f"   https://opinion.lawmaking.go.kr (국민참여입법센터)")
        return

    results = data.get("results", [])
    if not results:
        print("입법예고 검색 결과가 없습니다.")
        return

    status_str = "진행중" if args.status == "ongoing" else "완료"
    print(f"\n📜 입법예고 ({status_str}, {len(results)}건)")
    print("=" * 60)

    for item in results:
        print(f"\n📌 {item['title']}")
        print(f"   소관부처: {item['ministry']}")
        print(f"   예고번호: {item['notice_no']}")
        print(f"   예고기간: {item['start_date']} ~ {item['end_date']}")


# ============================================================
# 종합 요약
# ============================================================


def cmd_summary(args):
    """정책 동향 종합 요약"""
    print("\n" + "=" * 60)
    print("📊 정부 정책 집행 동향 요약")
    print("=" * 60)

    # 1. RSS 보도자료 (제재 관련)
    print("\n\n## 1. 최근 보도자료 (제재/정책 관련)")
    print("-" * 40)

    enforcement_keywords = ["제재", "과징금", "시정명령", "시정조치", "위반", "처분"]

    for dept_code, feed_info in RSS_FEEDS.items():
        if dept_code in ["ftc", "moel", "fsc", "pipc"]:  # 주요 부처만
            try:
                if HAS_FEEDPARSER:
                    results = fetch_rss(dept_code, limit=5)
                    relevant = [r for r in results if any(kw in r["title"] for kw in enforcement_keywords)]
                    if relevant:
                        print(f"\n### {feed_info['name']}")
                        for item in relevant[:3]:
                            print(f"  - {item['title'][:50]}...")
                            print(f"    {item['link']}")
            except Exception:
                pass

    # 2. 법령해석례 (최근)
    print("\n\n## 2. 최근 주요 법령해석례")
    print("-" * 40)

    for keyword in ["해고", "임금", "근로시간"]:
        try:
            data = search_legal_interpret(keyword, display=3)
            if data.get("error") == "auth_failed":
                print(f"\n  ⚠️ 법령해석례 API 권한 없음")
                print(f"     웹검색 대안: \"{keyword} 법령해석\" site:law.go.kr")
                break
            if data["results"]:
                print(f"\n### '{keyword}' 관련")
                for item in data["results"][:2]:
                    print(f"  - {item['title'][:50]}...")
        except Exception:
            pass

    # 3. 입법예고
    print("\n\n## 3. 진행중인 입법예고")
    print("-" * 40)

    try:
        data = search_legislative(status="ongoing", days=args.days, display=10)
        if data.get("error") == "auth_failed":
            print(f"  ⚠️ 입법예고 API 권한 없음")
            print(f"     대안: https://opinion.lawmaking.go.kr")
        elif data.get("results"):
            for item in data["results"][:5]:
                print(f"  - [{item['ministry']}] {item['title'][:40]}...")
                print(f"    예고기간: {item['start_date']} ~ {item['end_date']}")
        else:
            print("  (검색 결과 없음)")
    except Exception:
        print("  (검색 실패)")

    print("\n" + "=" * 60)
    print("💡 상세 정보는 개별 명령으로 확인하세요:")
    print("   python fetch_policy.py rss ftc --keyword 과징금")
    print("   python fetch_policy.py interpret 해고")
    print("   python fetch_policy.py legislative --status ongoing")


# ============================================================
# 프록시 상태 확인
# ============================================================


def cmd_proxy_status():
    """프록시 상태 확인 명령"""
    if not HAS_PROXY_UTILS:
        print("⚠️  proxy_utils.py를 찾을 수 없습니다.")
        print("   같은 디렉토리에 proxy_utils.py가 있는지 확인하세요.")
        return

    status = get_geo_status()

    print("\n" + "=" * 50)
    print("🌏 프록시 상태 확인")
    print("=" * 50)

    print(f"\n📍 현재 위치")
    print(f"   IP: {status['ip']}")
    print(f"   국가: {status['country']}")
    print(f"   해외 여부: {'예 (프록시 필요)' if status['is_overseas'] else '아니오 (국내)'}")

    print(f"\n⚙️  프록시 설정")
    print(f"   설정됨: {'예' if status['proxy_configured'] else '아니오'}")
    if status['proxy_configured']:
        print(f"   유형: {status['proxy_type']}")

    if status['is_overseas'] and not status['proxy_configured']:
        print("\n" + "-" * 50)
        print("⚠️  해외에서 실행 중이지만 프록시가 설정되지 않았습니다.")
        print("   한국 정부 API 접근이 차단될 수 있습니다.")
        print("\n📋 설정 방법:")
        print("   [Cloudflare Workers - 무료 권장]")
        print("   export BEOPSUNY_PROXY_TYPE=cloudflare")
        print("   export BEOPSUNY_PROXY_URL='https://your-worker.workers.dev'")
        print("\n   [Bright Data - 유료]")
        print("   export BEOPSUNY_PROXY_TYPE=brightdata")
        print("   export BEOPSUNY_BRIGHTDATA_USERNAME='your-username'")
        print("   export BEOPSUNY_BRIGHTDATA_PASSWORD='your-password'")
    else:
        print("\n✅ 프록시 상태 정상")


# ============================================================
# CLI
# ============================================================


def main():
    parser = argparse.ArgumentParser(
        description="정부 정책 집행 동향 수집",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # RSS 보도자료 수집
  python fetch_policy.py rss                    # 전체 부처
  python fetch_policy.py rss ftc                # 공정거래위원회만
  python fetch_policy.py rss ftc --keyword 과징금

  # 고용노동부 행정해석 검색
  python fetch_policy.py interpret "해고"
  python fetch_policy.py interpret "임금" --display 30

  # 입법예고 검색
  python fetch_policy.py legislative --status ongoing
  python fetch_policy.py legislative --law-name "근로기준법"

  # 종합 요약
  python fetch_policy.py summary --days 7

Available dept codes: ftc, moel, fsc, pipc, moleg
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="명령")

    # rss 명령
    rss_parser = subparsers.add_parser("rss", help="RSS 보도자료 수집")
    rss_parser.add_argument("dept", nargs="?", help="부처 코드 (ftc, moel, fsc, pipc, moleg)")
    rss_parser.add_argument("--keyword", "-k", help="키워드 필터")
    rss_parser.add_argument("--limit", "-l", type=int, default=20, help="최대 건수 (기본: 20)")

    # interpret 명령
    interpret_parser = subparsers.add_parser("interpret", help="고용노동부 행정해석 검색")
    interpret_parser.add_argument("query", help="검색어")
    interpret_parser.add_argument("--display", "-d", type=int, default=20, help="표시 건수")

    # legislative 명령
    leg_parser = subparsers.add_parser("legislative", help="입법예고 검색")
    leg_parser.add_argument("--status", "-s", choices=["ongoing", "completed"], default="ongoing", help="상태")
    leg_parser.add_argument("--law-name", "-n", help="법령명")
    leg_parser.add_argument("--days", "-d", type=int, default=30, help="검색 기간 (일)")
    leg_parser.add_argument("--display", type=int, default=20, help="표시 건수")

    # summary 명령
    summary_parser = subparsers.add_parser("summary", help="정책 동향 종합 요약")
    summary_parser.add_argument("--days", "-d", type=int, default=7, help="검색 기간 (일)")

    # proxy-status 명령
    proxy_parser = subparsers.add_parser("proxy-status", help="프록시 상태 확인")

    args = parser.parse_args()

    # 프록시 상태 명령
    if args.command == "proxy-status":
        cmd_proxy_status()
        return

    if args.command == "rss":
        cmd_rss(args)
    elif args.command == "interpret":
        cmd_interpret(args)
    elif args.command == "legislative":
        cmd_legislative(args)
    elif args.command == "summary":
        cmd_summary(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
