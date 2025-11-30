#!/usr/bin/env python3
"""
Proxy Utilities for Korean Government API Access

한국 정부 API (law.go.kr, korea.kr 등)는 해외 IP를 차단합니다.
이 모듈은 해외 실행 환경(Claude Code Web, Codex Web 등)에서
자동으로 프록시를 통해 API에 접근할 수 있도록 지원합니다.

Supported proxy methods (우선순위 순):
1. Cloudflare Workers (권장) - 무료 10만 req/일, 빠름
2. Bright Data - 한국 Residential IP, 유료 ($5.04/GB~)
3. Generic HTTP/HTTPS Proxy

Usage:
    from proxy_utils import fetch_with_proxy, is_overseas, get_geo_status

    # 자동 판단 (해외면 프록시, 국내면 직접)
    content = fetch_with_proxy("https://law.go.kr/...")

    # 상태 확인
    print(get_geo_status())

Environment Variables:
    BEOPSUNY_PROXY_TYPE: cloudflare | brightdata | http (기본: cloudflare)
    BEOPSUNY_PROXY_URL: 프록시 URL (Cloudflare Worker URL 또는 Bright Data endpoint)
    BEOPSUNY_BRIGHTDATA_USERNAME: Bright Data 사용자명
    BEOPSUNY_BRIGHTDATA_PASSWORD: Bright Data 비밀번호
    BEOPSUNY_FORCE_PROXY: 항상 프록시 사용 (1/true/yes)
    BEOPSUNY_SKIP_GEO_CHECK: 지역 체크 스킵 (1/true/yes)
"""

import base64
import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

# 스크립트 위치 기준 경로
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR.parent / "config" / "settings.yaml"

# 환경변수 이름
ENV_PROXY_TYPE = "BEOPSUNY_PROXY_TYPE"  # cloudflare, brightdata, http
ENV_PROXY_URL = "BEOPSUNY_PROXY_URL"
ENV_BRIGHTDATA_USERNAME = "BEOPSUNY_BRIGHTDATA_USERNAME"
ENV_BRIGHTDATA_PASSWORD = "BEOPSUNY_BRIGHTDATA_PASSWORD"
ENV_FORCE_PROXY = "BEOPSUNY_FORCE_PROXY"
ENV_SKIP_GEO_CHECK = "BEOPSUNY_SKIP_GEO_CHECK"

# Bright Data 기본 설정 (한국 Residential)
BRIGHTDATA_DEFAULT_HOST = "brd.superproxy.io"
BRIGHTDATA_DEFAULT_PORT = 22225
BRIGHTDATA_COUNTRY = "kr"  # 한국

# IP 지역 확인 서비스 (무료)
GEO_CHECK_SERVICES = [
    ("https://ipapi.co/json/", "country_code"),
    ("https://ip-api.com/json/", "countryCode"),
    ("https://ipinfo.io/json", "country"),
]

# 한국 국가 코드
KOREA_COUNTRY_CODES = {"KR", "KOR"}

# 캐시
_geo_cache: Optional[Dict[str, Any]] = None
_config_cache: Optional[Dict[str, Any]] = None


def _load_config() -> Dict[str, Any]:
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


def _get_geo_info() -> Dict[str, Any]:
    """현재 IP의 지역 정보 조회 (캐싱)"""
    global _geo_cache
    if _geo_cache is not None:
        return _geo_cache

    for service_url, country_field in GEO_CHECK_SERVICES:
        try:
            req = urllib.request.Request(
                service_url,
                headers={"User-Agent": "Beopsuny/1.0"},
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
                _geo_cache = {
                    "country": data.get(country_field, ""),
                    "ip": data.get("ip", data.get("query", "")),
                    "service": service_url,
                }
                return _geo_cache
        except Exception:
            continue

    # 모든 서비스 실패 시 기본값
    _geo_cache = {"country": "UNKNOWN", "ip": "", "service": ""}
    return _geo_cache


def is_overseas() -> bool:
    """현재 실행 환경이 해외인지 확인

    Returns:
        True: 해외 (프록시 필요)
        False: 국내 (직접 접근 가능)
    """
    # 환경변수로 강제 설정
    if os.environ.get(ENV_FORCE_PROXY, "").lower() in ("1", "true", "yes"):
        return True

    if os.environ.get(ENV_SKIP_GEO_CHECK, "").lower() in ("1", "true", "yes"):
        return False

    # 설정 파일 확인
    config = _load_config()
    proxy_config = config.get("proxy", {})

    if proxy_config.get("force_proxy", False):
        return True

    if proxy_config.get("skip_geo_check", False):
        return False

    # IP 지역 확인
    try:
        geo = _get_geo_info()
        country = geo.get("country", "").upper()
        return country not in KOREA_COUNTRY_CODES
    except Exception:
        # 확인 실패 시 해외로 가정 (안전)
        return True


def get_proxy_config() -> Dict[str, Any]:
    """프록시 설정 로드

    Returns:
        프록시 설정 딕셔너리:
        - type: cloudflare | brightdata | http
        - url: 프록시 URL
        - username: (brightdata) 사용자명
        - password: (brightdata) 비밀번호
    """
    result = {
        "type": None,
        "url": None,
        "username": None,
        "password": None,
    }

    # 1. 환경변수 우선
    proxy_type = os.environ.get(ENV_PROXY_TYPE, "").lower()
    proxy_url = os.environ.get(ENV_PROXY_URL)
    bd_username = os.environ.get(ENV_BRIGHTDATA_USERNAME)
    bd_password = os.environ.get(ENV_BRIGHTDATA_PASSWORD)

    if proxy_type or proxy_url or bd_username:
        result["type"] = proxy_type or "cloudflare"
        result["url"] = proxy_url
        result["username"] = bd_username
        result["password"] = bd_password
        return result

    # 2. 설정 파일
    config = _load_config()
    proxy_config = config.get("proxy", {})

    result["type"] = proxy_config.get("type", "cloudflare")
    result["url"] = proxy_config.get("url")

    # Bright Data 설정
    brightdata = proxy_config.get("brightdata", {})
    result["username"] = brightdata.get("username")
    result["password"] = brightdata.get("password")

    return result


def fetch_via_cloudflare_worker(
    url: str,
    proxy_url: str,
    timeout: int = 30,
    headers: Optional[Dict[str, str]] = None,
) -> str:
    """Cloudflare Worker 프록시를 통해 URL 가져오기

    Worker는 두 가지 형식 지원:
    1. GET /?url=<encoded_url>
    2. POST / with {"url": "...", "headers": {...}}

    Args:
        url: 요청할 URL
        proxy_url: Worker URL
        timeout: 타임아웃 (초)
        headers: 추가 헤더

    Returns:
        응답 본문

    Raises:
        RuntimeError: 프록시 요청 실패 시
    """
    # URL 파라미터로 전달 (GET 방식)
    encoded_url = urllib.parse.quote(url, safe="")
    full_url = f"{proxy_url}?url={encoded_url}"

    req_headers = {"User-Agent": "Beopsuny/1.0"}
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(full_url, headers=req_headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8")

    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Cloudflare Worker HTTP error: {e.code}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Cloudflare Worker URL error: {e.reason}") from e
    except socket.timeout:
        raise RuntimeError(f"Cloudflare Worker timeout after {timeout}s") from None


def fetch_via_brightdata(
    url: str,
    username: str,
    password: str,
    timeout: int = 30,
    headers: Optional[Dict[str, str]] = None,
    host: str = BRIGHTDATA_DEFAULT_HOST,
    port: int = BRIGHTDATA_DEFAULT_PORT,
) -> str:
    """Bright Data 프록시를 통해 URL 가져오기 (한국 Residential IP)

    Args:
        url: 요청할 URL
        username: Bright Data 사용자명 (zone 포함)
        password: Bright Data 비밀번호
        timeout: 타임아웃 (초)
        headers: 추가 헤더
        host: Bright Data 호스트
        port: Bright Data 포트

    Returns:
        응답 본문

    Raises:
        RuntimeError: 프록시 요청 실패 시
    """
    # 한국 국가 지정 추가
    if "-country-" not in username:
        username = f"{username}-country-{BRIGHTDATA_COUNTRY}"

    # 프록시 URL 구성
    proxy_url = f"http://{username}:{password}@{host}:{port}"

    # 프록시 핸들러 설정
    proxy_handler = urllib.request.ProxyHandler({
        "http": proxy_url,
        "https": proxy_url,
    })
    opener = urllib.request.build_opener(proxy_handler)

    req_headers = {"User-Agent": "Beopsuny/1.0"}
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, headers=req_headers)

    try:
        with opener.open(req, timeout=timeout) as response:
            return response.read().decode("utf-8")

    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Bright Data HTTP error: {e.code}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Bright Data URL error: {e.reason}") from e
    except socket.timeout:
        raise RuntimeError(f"Bright Data timeout after {timeout}s") from None


def fetch_via_http_proxy(
    url: str,
    proxy_url: str,
    timeout: int = 30,
    headers: Optional[Dict[str, str]] = None,
) -> str:
    """일반 HTTP/HTTPS 프록시를 통해 URL 가져오기

    Args:
        url: 요청할 URL
        proxy_url: 프록시 URL (http://user:pass@host:port)
        timeout: 타임아웃 (초)
        headers: 추가 헤더

    Returns:
        응답 본문

    Raises:
        RuntimeError: 프록시 요청 실패 시
    """
    proxy_handler = urllib.request.ProxyHandler({
        "http": proxy_url,
        "https": proxy_url,
    })
    opener = urllib.request.build_opener(proxy_handler)

    req_headers = {"User-Agent": "Beopsuny/1.0"}
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, headers=req_headers)

    try:
        with opener.open(req, timeout=timeout) as response:
            return response.read().decode("utf-8")

    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP proxy error: {e.code}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"HTTP proxy URL error: {e.reason}") from e
    except socket.timeout:
        raise RuntimeError(f"HTTP proxy timeout after {timeout}s") from None


def fetch_with_proxy(
    url: str,
    timeout: int = 30,
    headers: Optional[Dict[str, str]] = None,
    force_proxy: bool = False,
) -> str:
    """자동으로 프록시 필요 여부를 판단하여 URL 가져오기

    해외 실행 환경이면 프록시를 사용하고,
    국내이면 직접 접근합니다.

    프록시 우선순위:
    1. Cloudflare Workers (무료, 빠름)
    2. Bright Data (유료, 안정)
    3. Generic HTTP Proxy

    Args:
        url: 요청할 URL
        timeout: 타임아웃 (초)
        headers: 추가 헤더
        force_proxy: 강제 프록시 사용

    Returns:
        응답 본문

    Raises:
        RuntimeError: 요청 실패 시
        ValueError: 프록시 미설정 시 (해외 환경)
    """
    use_proxy = force_proxy or is_overseas()

    if not use_proxy:
        # 국내: 직접 접근
        req_headers = {"User-Agent": "Beopsuny/1.0"}
        if headers:
            req_headers.update(headers)

        req = urllib.request.Request(url, headers=req_headers)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP error {e.code}: {e.reason}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"URL error: {e.reason}") from e
        except socket.timeout:
            raise RuntimeError(f"Request timeout after {timeout}s") from None

    # 해외: 프록시 사용
    config = get_proxy_config()
    proxy_type = config.get("type", "cloudflare")

    if proxy_type == "cloudflare":
        proxy_url = config.get("url")
        if not proxy_url:
            raise ValueError(
                "Cloudflare Worker URL not configured.\n"
                f"Set {ENV_PROXY_URL} or configure in settings.yaml.\n"
                "See: docs/PROXY_SETUP.md"
            )
        return fetch_via_cloudflare_worker(url, proxy_url, timeout, headers)

    elif proxy_type == "brightdata":
        username = config.get("username")
        password = config.get("password")
        if not username or not password:
            raise ValueError(
                "Bright Data credentials not configured.\n"
                f"Set {ENV_BRIGHTDATA_USERNAME} and {ENV_BRIGHTDATA_PASSWORD}\n"
                "or configure in settings.yaml.\n"
                "See: docs/PROXY_SETUP.md"
            )
        return fetch_via_brightdata(url, username, password, timeout, headers)

    elif proxy_type == "http":
        proxy_url = config.get("url")
        if not proxy_url:
            raise ValueError(
                "HTTP proxy URL not configured.\n"
                f"Set {ENV_PROXY_URL} or configure in settings.yaml."
            )
        return fetch_via_http_proxy(url, proxy_url, timeout, headers)

    else:
        raise ValueError(f"Unknown proxy type: {proxy_type}")


def get_geo_status() -> Dict[str, Any]:
    """현재 지역 상태 정보 반환 (디버깅용)"""
    geo = _get_geo_info()
    config = get_proxy_config()

    proxy_configured = bool(
        config.get("url") or
        (config.get("username") and config.get("password"))
    )

    return {
        "ip": geo.get("ip", ""),
        "country": geo.get("country", ""),
        "is_overseas": is_overseas(),
        "proxy_configured": proxy_configured,
        "proxy_type": config.get("type") if proxy_configured else None,
    }


def test_proxy_connection() -> Dict[str, Any]:
    """프록시 연결 테스트

    Returns:
        테스트 결과:
        - success: 성공 여부
        - proxy_ip: 프록시 통한 IP
        - proxy_country: 프록시 국가
        - error: 에러 메시지 (실패 시)
    """
    test_url = "https://ipapi.co/json/"

    try:
        content = fetch_with_proxy(test_url, force_proxy=True)
        data = json.loads(content)
        return {
            "success": True,
            "proxy_ip": data.get("ip", ""),
            "proxy_country": data.get("country_code", ""),
            "is_korea": data.get("country_code", "").upper() in KOREA_COUNTRY_CODES,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


# CLI 테스트용
if __name__ == "__main__":
    import sys

    print("=" * 50)
    print("🌏 Beopsuny Proxy Utils - 상태 확인")
    print("=" * 50)

    # 1. 현재 위치 확인
    status = get_geo_status()
    print(f"\n📍 현재 위치")
    print(f"   IP: {status['ip']}")
    print(f"   국가: {status['country']}")
    print(f"   해외 여부: {'예 (프록시 필요)' if status['is_overseas'] else '아니오 (국내)'}")

    # 2. 프록시 설정 확인
    print(f"\n⚙️  프록시 설정")
    print(f"   설정됨: {'예' if status['proxy_configured'] else '아니오'}")
    if status['proxy_configured']:
        print(f"   유형: {status['proxy_type']}")

    # 3. 해외이고 프록시 미설정 시 안내
    if status['is_overseas'] and not status['proxy_configured']:
        print("\n" + "=" * 50)
        print("⚠️  해외에서 실행 중이지만 프록시가 설정되지 않았습니다.")
        print("   한국 정부 API (law.go.kr, korea.kr) 접근이 차단됩니다.")
        print("\n📋 설정 방법:")
        print("\n   [옵션 1] Cloudflare Workers (무료, 권장)")
        print(f"   export {ENV_PROXY_TYPE}=cloudflare")
        print(f"   export {ENV_PROXY_URL}='https://your-worker.workers.dev'")
        print("\n   [옵션 2] Bright Data (유료, 안정)")
        print(f"   export {ENV_PROXY_TYPE}=brightdata")
        print(f"   export {ENV_BRIGHTDATA_USERNAME}='your-username'")
        print(f"   export {ENV_BRIGHTDATA_PASSWORD}='your-password'")
        print("\n   자세한 설정: docs/PROXY_SETUP.md")
        sys.exit(1)

    # 4. 프록시 연결 테스트 (설정된 경우)
    if status['proxy_configured'] and status['is_overseas']:
        print("\n🔌 프록시 연결 테스트 중...")
        test_result = test_proxy_connection()

        if test_result['success']:
            print(f"   ✅ 성공!")
            print(f"   프록시 IP: {test_result['proxy_ip']}")
            print(f"   프록시 국가: {test_result['proxy_country']}")
            if test_result.get('is_korea'):
                print("   🇰🇷 한국 IP 확인됨 - API 접근 가능")
            else:
                print("   ⚠️ 한국 IP가 아님 - 일부 API 차단 가능")
        else:
            print(f"   ❌ 실패: {test_result['error']}")
            sys.exit(1)

    print("\n" + "=" * 50)
    print("✅ 프록시 설정 상태 정상")
