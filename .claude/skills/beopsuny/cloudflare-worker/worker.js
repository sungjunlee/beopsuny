/**
 * Beopsuny Proxy Worker for Cloudflare Workers
 *
 * 한국 정부 API (law.go.kr, korea.kr 등)에 대한 프록시 워커입니다.
 * 해외에서 차단된 한국 정부 API에 접근할 수 있게 해줍니다.
 *
 * 배포 방법:
 * 1. https://dash.cloudflare.com 에서 Workers 생성
 * 2. 이 코드를 붙여넣기
 * 3. 배포 후 URL 복사 (예: https://your-worker.workers.dev)
 * 4. 환경변수 설정: export BEOPSUNY_PROXY_URL='https://your-worker.workers.dev'
 *
 * 사용법:
 * GET /?url=https://law.go.kr/...
 *
 * 보안:
 * - 허용된 도메인만 프록시 (law.go.kr, korea.kr 등)
 * - 선택적 API 키 인증 지원
 */

// 허용된 프록시 대상 도메인
const ALLOWED_DOMAINS = [
  'law.go.kr',
  'www.law.go.kr',
  'open.law.go.kr',
  'korea.kr',
  'www.korea.kr',
  'opinion.lawmaking.go.kr',
  'open.assembly.go.kr',
  'likms.assembly.go.kr',
  'data.go.kr',
  'www.data.go.kr',
];

// CORS 헤더
const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key',
};

/**
 * 요청 처리
 */
export default {
  async fetch(request, env) {
    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS_HEADERS });
    }

    try {
      // API 키 검증 (선택적)
      if (env.API_KEY) {
        const apiKey = request.headers.get('X-API-Key') ||
                       new URL(request.url).searchParams.get('api_key');
        if (apiKey !== env.API_KEY) {
          return jsonResponse({ error: 'Invalid API key' }, 401);
        }
      }

      // URL 파라미터에서 대상 URL 추출
      const url = new URL(request.url);
      const targetUrl = url.searchParams.get('url');

      if (!targetUrl) {
        return jsonResponse({
          error: 'Missing url parameter',
          usage: 'GET /?url=https://law.go.kr/...',
          allowed_domains: ALLOWED_DOMAINS,
        }, 400);
      }

      // URL 검증
      let parsedUrl;
      try {
        parsedUrl = new URL(targetUrl);
      } catch (e) {
        return jsonResponse({ error: 'Invalid URL format' }, 400);
      }

      // 도메인 검증
      const hostname = parsedUrl.hostname.toLowerCase();
      const isAllowed = ALLOWED_DOMAINS.some(domain =>
        hostname === domain || hostname.endsWith('.' + domain)
      );

      if (!isAllowed) {
        return jsonResponse({
          error: 'Domain not allowed',
          domain: hostname,
          allowed_domains: ALLOWED_DOMAINS,
        }, 403);
      }

      // 프록시 요청
      const proxyResponse = await fetch(targetUrl, {
        method: request.method,
        headers: {
          'User-Agent': 'Mozilla/5.0 (compatible; Beopsuny/1.0)',
          'Accept': '*/*',
          'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
        },
        redirect: 'follow',
      });

      // 응답 반환 (원본 Content-Type 유지)
      const contentType = proxyResponse.headers.get('Content-Type') || 'text/plain';
      const body = await proxyResponse.text();

      return new Response(body, {
        status: proxyResponse.status,
        headers: {
          'Content-Type': contentType,
          ...CORS_HEADERS,
          'X-Proxied-From': hostname,
        },
      });

    } catch (error) {
      return jsonResponse({
        error: 'Proxy error',
        message: error.message,
      }, 500);
    }
  },
};

/**
 * JSON 응답 헬퍼
 */
function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...CORS_HEADERS,
    },
  });
}
