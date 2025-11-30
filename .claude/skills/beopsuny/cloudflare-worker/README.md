# Beopsuny Proxy - Cloudflare Worker

한국 정부 API (law.go.kr, korea.kr 등)에 대한 프록시 워커입니다.

## 왜 필요한가?

한국 정부 API는 해외 IP를 차단합니다. Claude Code Web, Codex Web 등
해외 서버에서 실행되는 환경에서는 직접 접근이 불가능합니다.

이 워커를 배포하면 Cloudflare의 글로벌 네트워크를 통해
한국 정부 API에 접근할 수 있습니다.

## 비용

- **무료 플랜**: 100,000 요청/일 (대부분의 사용에 충분)
- **유료 플랜**: $5/월 (10,000,000 요청/월)

## 배포 방법

### 방법 1: Cloudflare 대시보드 (간단)

1. [Cloudflare Dashboard](https://dash.cloudflare.com) 접속
2. **Workers & Pages** → **Create Application** → **Create Worker**
3. 이름 입력 (예: `beopsuny-proxy`)
4. **Deploy** 클릭
5. **Edit code** 클릭
6. `worker.js` 내용을 붙여넣기
7. **Save and Deploy**
8. 생성된 URL 복사 (예: `https://beopsuny-proxy.your-account.workers.dev`)

### 방법 2: Wrangler CLI (개발자용)

```bash
# Wrangler 설치
npm install -g wrangler

# Cloudflare 로그인
wrangler login

# 배포
cd .claude/skills/beopsuny/cloudflare-worker
npx wrangler deploy
```

## 사용법

### 환경변수 설정

```bash
# Cloudflare Worker 사용
export BEOPSUNY_PROXY_TYPE=cloudflare
export BEOPSUNY_PROXY_URL='https://beopsuny-proxy.your-account.workers.dev'
```

### 테스트

```bash
# 직접 테스트
curl "https://beopsuny-proxy.your-account.workers.dev/?url=https://law.go.kr"

# Python 테스트
python .claude/skills/beopsuny/scripts/proxy_utils.py
```

## 보안

### 허용된 도메인

워커는 다음 도메인만 프록시합니다:
- law.go.kr (국가법령정보센터)
- korea.kr (정책브리핑)
- opinion.lawmaking.go.kr (입법예고)
- open.assembly.go.kr (열린국회정보)
- data.go.kr (공공데이터포털)

### API 키 설정 (선택)

공개 URL이 노출되는 것이 우려되면 API 키를 설정할 수 있습니다:

1. Cloudflare 대시보드 → Workers → 설정 → 환경 변수
2. `API_KEY` 변수 추가
3. 요청 시 헤더 또는 파라미터로 전달:
   ```
   GET /?url=...&api_key=your-secret
   # 또는
   X-API-Key: your-secret
   ```

## 문제 해결

### 403 Forbidden

- 허용되지 않은 도메인에 접근 시도
- `worker.js`의 `ALLOWED_DOMAINS` 확인

### 401 Unauthorized

- API 키가 설정되었으나 요청에 포함되지 않음
- API 키 확인

### 504 Gateway Timeout

- 대상 서버 응답 지연
- 타임아웃 설정 확인 (기본 30초)

## 참고

- [Cloudflare Workers 문서](https://developers.cloudflare.com/workers/)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/)
