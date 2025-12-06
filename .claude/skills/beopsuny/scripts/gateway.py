#!/usr/bin/env python3
"""
Gateway - HTTP Fetch Gateway for Korean Government API Access

한국 정부 API (law.go.kr, korea.kr 등)는 해외 IP를 차단합니다.
이 모듈은 cors-anywhere 기반 게이트웨이를 통해 해외에서도 API에 접근할 수 있도록 지원합니다.

게이트웨이는 URL을 Base64URL로 인코딩하여 Cloudflare WAF 우회를 지원합니다.

Usage:
    from gateway import fetch_with_gateway, fetch_url, is_gateway_configured

    # 게이트웨이를 통해 URL 가져오기
    content = fetch_with_gateway("http://law.go.kr/...")

    # 자동 판단 (게이트웨이 설정 시 사용, 아니면 직접 접근)
    content = fetch_url("http://law.go.kr/...")

    # 설정 확인
    if is_gateway_configured():
        print("Gateway ready")

Environment Variables:
    BEOPSUNY_GATEWAY_URL: cors-anywhere 게이트웨이 URL
    BEOPSUNY_GATEWAY_API_KEY: API 키 (선택, 게이트웨이에서 인증 설정 시)
"""

import os
import socket
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

import yaml

# 스크립트 위치 기준 경로
SCRIPT_DIR = Path(__file__).parent
CONFIG_PATH = SCRIPT_DIR.parent / "config" / "settings.yaml"

# 환경변수 이름
ENV_GATEWAY_URL = "BEOPSUNY_GATEWAY_URL"
ENV_GATEWAY_API_KEY = "BEOPSUNY_GATEWAY_API_KEY"

# 캐시
_config_cache: Optional[dict] = None


def _load_config() -> dict:
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


def get_gateway_config() -> dict:
    """게이트웨이 설정 로드

    Returns:
        게이트웨이 설정:
        - url: 게이트웨이 URL
        - api_key: API 키 (선택)
    """
    result = {
        "url": None,
        "api_key": None,
    }

    # 1. 환경변수 우선
    gateway_url = os.environ.get(ENV_GATEWAY_URL)
    api_key = os.environ.get(ENV_GATEWAY_API_KEY)

    if gateway_url:
        result["url"] = gateway_url.rstrip("/")
        result["api_key"] = api_key
        return result

    # 2. 설정 파일
    config = _load_config()
    gateway_config = config.get("gateway", {})

    result["url"] = gateway_config.get("url", "").rstrip("/") or None
    result["api_key"] = gateway_config.get("api_key")

    return result


def is_gateway_configured() -> bool:
    """게이트웨이가 설정되어 있는지 확인"""
    config = get_gateway_config()
    return bool(config.get("url"))


def _encode_url_for_gateway(url: str) -> str:
    """URL을 Base64URL로 인코딩 (Cloudflare WAF 우회용)

    Args:
        url: 인코딩할 URL

    Returns:
        Base64URL 인코딩된 문자열
    """
    import base64
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip('=')


def fetch_with_gateway(
    url: str,
    timeout: int = 30,
    headers: Optional[dict] = None,
) -> str:
    """cors-anywhere 게이트웨이를 통해 URL 가져오기

    URL은 Base64URL로 인코딩되어 /fetch/{encoded} 엔드포인트로 전송됩니다.
    이는 Cloudflare WAF의 Open Proxy 패턴 탐지를 우회하기 위함입니다.

    Args:
        url: 요청할 URL
        timeout: 타임아웃 (초)
        headers: 추가 헤더

    Returns:
        응답 본문 (문자열)

    Raises:
        ValueError: 게이트웨이 미설정 시
        RuntimeError: 요청 실패 시
    """
    config = get_gateway_config()
    gateway_url = config.get("url")

    if not gateway_url:
        raise ValueError(
            "Gateway not configured.\n"
            f"Set {ENV_GATEWAY_URL} environment variable.\n"
            "Example: export BEOPSUNY_GATEWAY_URL='https://your-gateway.example.com'"
        )

    # Base64URL 인코딩 방식: {gateway}/fetch/{encoded_url}
    encoded_url = _encode_url_for_gateway(url)
    full_url = f"{gateway_url}/fetch/{encoded_url}"

    # 헤더 설정
    req_headers = {"User-Agent": "Beopsuny/1.0"}

    # API 키 추가 (설정된 경우)
    api_key = config.get("api_key")
    if api_key:
        req_headers["x-api-key"] = api_key

    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(full_url, headers=req_headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8")

    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise RuntimeError(
                "Gateway authentication failed (401).\n"
                f"Check your API key: {ENV_GATEWAY_API_KEY}"
            ) from e
        elif e.code == 403:
            config = get_gateway_config()
            if not config.get("api_key"):
                raise RuntimeError(
                    "Gateway access forbidden (403).\n"
                    "API key is required but not configured.\n"
                    f"Set {ENV_GATEWAY_API_KEY} environment variable or add api_key to settings.yaml"
                ) from e
            else:
                raise RuntimeError(
                    "Gateway access forbidden (403).\n"
                    "The API key may be invalid or the gateway blocked this request."
                ) from e
        raise RuntimeError(f"Gateway HTTP error: {e.code} {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Gateway URL error: {e.reason}") from e
    except socket.timeout:
        raise RuntimeError(f"Gateway timeout after {timeout}s") from None


def fetch_direct(
    url: str,
    timeout: int = 30,
    headers: Optional[dict] = None,
) -> str:
    """직접 URL 가져오기 (게이트웨이 없이)

    Args:
        url: 요청할 URL
        timeout: 타임아웃 (초)
        headers: 추가 헤더

    Returns:
        응답 본문 (문자열)

    Raises:
        RuntimeError: 요청 실패 시
    """
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


def fetch_url(
    url: str,
    timeout: int = 30,
    headers: Optional[dict] = None,
    use_gateway: Optional[bool] = None,
) -> str:
    """URL 가져오기 (게이트웨이 자동 판단)

    게이트웨이가 설정되어 있으면 게이트웨이를 사용하고,
    그렇지 않으면 직접 접근합니다.

    Args:
        url: 요청할 URL
        timeout: 타임아웃 (초)
        headers: 추가 헤더
        use_gateway: 게이트웨이 사용 여부 (None이면 자동 판단)

    Returns:
        응답 본문 (문자열)
    """
    if use_gateway is None:
        use_gateway = is_gateway_configured()

    if use_gateway:
        return fetch_with_gateway(url, timeout, headers)
    else:
        return fetch_direct(url, timeout, headers)


# 하위 호환성을 위한 별칭
def fetch_with_proxy(
    url: str,
    timeout: int = 30,
    headers: Optional[dict] = None,
    force_proxy: bool = False,
) -> str:
    """(하위 호환) fetch_url의 별칭

    기존 코드와의 호환성을 위해 유지됩니다.
    새 코드는 fetch_url() 또는 fetch_with_gateway()를 사용하세요.
    """
    return fetch_url(url, timeout, headers, use_gateway=force_proxy or None)


def is_overseas() -> bool:
    """(하위 호환) 항상 게이트웨이 설정 여부 반환

    기존 코드와의 호환성을 위해 유지됩니다.
    새 코드는 is_gateway_configured()를 사용하세요.
    """
    return is_gateway_configured()


def get_geo_status() -> dict:
    """(하위 호환) 상태 정보 반환"""
    config = get_gateway_config()
    return {
        "gateway_configured": is_gateway_configured(),
        "gateway_url": config.get("url"),
        "has_api_key": bool(config.get("api_key")),
    }


# CLI 테스트용
if __name__ == "__main__":
    import sys

    print("=" * 50)
    print("🌏 Beopsuny Gateway Utils - 상태 확인")
    print("=" * 50)

    config = get_gateway_config()
    configured = is_gateway_configured()

    print(f"\n⚙️  게이트웨이 설정")
    print(f"   설정됨: {'예' if configured else '아니오'}")

    if configured:
        print(f"   URL: {config['url']}")
        print(f"   API 키: {'설정됨' if config['api_key'] else '없음'}")

        # 연결 테스트
        print("\n🔌 게이트웨이 연결 테스트...")
        try:
            # 간단한 테스트 URL
            test_url = "http://www.google.com"
            content = fetch_with_gateway(test_url, timeout=10)
            if "google" in content.lower():
                print("   ✅ 게이트웨이 연결 성공!")
            else:
                print("   ⚠️ 응답은 받았지만 예상과 다름")
        except Exception as e:
            print(f"   ❌ 연결 실패: {e}")
            sys.exit(1)

        # law.go.kr 테스트
        print("\n📜 law.go.kr API 테스트...")
        try:
            import urllib.parse
            query = urllib.parse.quote("민법")
            test_url = f"http://www.law.go.kr/DRF/lawSearch.do?OC=test&target=law&type=XML&query={query}&display=1"
            content = fetch_with_gateway(test_url, timeout=15)
            if "<law>" in content or "LawSearch" in content:
                print("   ✅ law.go.kr API 접근 성공!")
            elif "<!DOCTYPE" in content or "<html" in content:
                print("   ⚠️ HTML 응답 - OC 코드 확인 필요")
            else:
                print("   ⚠️ 예상치 못한 응답")
        except Exception as e:
            print(f"   ❌ API 접근 실패: {e}")

    else:
        print("\n" + "=" * 50)
        print("⚠️  게이트웨이가 설정되지 않았습니다.")
        print("\n📋 설정 방법:")
        print(f"\n   export {ENV_GATEWAY_URL}='https://your-gateway.example.com'")
        print(f"\n   # API 키가 필요한 경우:")
        print(f"   export {ENV_GATEWAY_API_KEY}='your-api-key'")
        sys.exit(1)

    print("\n" + "=" * 50)
    print("✅ 설정 상태 정상")
