# 프록시 설정 가이드 (해외 접근용)

한국 정부 API (law.go.kr, korea.kr 등)는 해외 IP를 차단합니다.
Claude Code Web, Codex Web 등 해외 서버에서 실행되는 환경에서는 프록시 설정이 필요합니다.

## 왜 필요한가?

- **law.go.kr**: 국가법령정보센터 API - 해외 IP 차단
- **korea.kr**: 정책브리핑 RSS - 일부 해외 IP 차단
- **opinion.lawmaking.go.kr**: 입법예고 API - 해외 IP 차단

이러한 API들은 한국 내 IP에서만 접근 가능합니다.

## 자동 감지

Beopsuny는 실행 환경의 IP를 자동으로 감지하여:
- **국내 IP**: 직접 API 접근
- **해외 IP**: 프록시를 통한 API 접근

## 프록시 옵션 비교

| 옵션 | 비용 | 장점 | 단점 |
|------|------|------|------|
| **Cloudflare Workers** | 무료 (10만 req/일) | 빠름, 간단 | 직접 배포 필요 |
| **Bright Data** | $5.04/GB~ | 안정적, 한국 Residential IP | 유료, 계정 필요 |
| **자체 HTTP 프록시** | 다양 | 완전 제어 | 직접 구축 필요 |

## 옵션 1: Cloudflare Workers (권장)

무료이고 설정이 간단합니다.

### 1단계: Worker 배포

**방법 A: Cloudflare 대시보드**

1. [Cloudflare Dashboard](https://dash.cloudflare.com) 접속
2. **Workers & Pages** → **Create Application** → **Create Worker**
3. 이름 입력 (예: `beopsuny-proxy`)
4. **Deploy** 클릭
5. **Edit code** 클릭
6. `.claude/skills/beopsuny/cloudflare-worker/worker.js` 내용 붙여넣기
7. **Save and Deploy**
8. URL 복사 (예: `https://beopsuny-proxy.your-account.workers.dev`)

**방법 B: Wrangler CLI**

```bash
# Wrangler 설치
npm install -g wrangler

# 로그인
wrangler login

# 배포
cd .claude/skills/beopsuny/cloudflare-worker
npx wrangler deploy
```

### 2단계: 환경변수 설정

```bash
export BEOPSUNY_PROXY_TYPE=cloudflare
export BEOPSUNY_PROXY_URL='https://beopsuny-proxy.your-account.workers.dev'
```

또는 `settings.yaml`:

```yaml
proxy:
  type: "cloudflare"
  url: "https://beopsuny-proxy.your-account.workers.dev"
```

### 3단계: 테스트

```bash
python .claude/skills/beopsuny/scripts/proxy_utils.py
```

## 옵션 2: Bright Data

안정적인 한국 Residential IP를 제공합니다.

### 1단계: Bright Data 가입

1. [Bright Data](https://brightdata.com) 가입
2. **Residential Proxies** 선택
3. Zone 생성 (한국 선택)
4. Username과 Password 확인

### 2단계: 환경변수 설정

```bash
export BEOPSUNY_PROXY_TYPE=brightdata
export BEOPSUNY_BRIGHTDATA_USERNAME='brd-customer-xxx-zone-korea'
export BEOPSUNY_BRIGHTDATA_PASSWORD='your-password'
```

또는 `settings.yaml`:

```yaml
proxy:
  type: "brightdata"
  brightdata:
    username: "brd-customer-xxx-zone-korea"
    password: "your-password"
```

### 비용 참고

- Residential: $5.04/GB (Pay-as-you-go)
- 법령 검색 1회당 약 10-50KB → 1GB로 약 20,000-100,000회 검색 가능

## 옵션 3: 자체 HTTP 프록시

한국에 VPS가 있다면 직접 프록시를 구축할 수 있습니다.

```bash
export BEOPSUNY_PROXY_TYPE=http
export BEOPSUNY_PROXY_URL='http://user:pass@your-proxy:port'
```

## 프록시 상태 확인

```bash
# 프록시 상태 확인
python .claude/skills/beopsuny/scripts/proxy_utils.py

# 또는
python .claude/skills/beopsuny/scripts/fetch_policy.py proxy-status
```

출력 예시:
```
📍 현재 위치
   IP: 1.2.3.4
   국가: US
   해외 여부: 예 (프록시 필요)

⚙️  프록시 설정
   설정됨: 예
   유형: cloudflare

✅ 프록시 설정 상태 정상
```

## 환경변수 요약

| 변수 | 설명 | 예시 |
|------|------|------|
| `BEOPSUNY_PROXY_TYPE` | 프록시 유형 | `cloudflare`, `brightdata`, `http` |
| `BEOPSUNY_PROXY_URL` | 프록시 URL | `https://worker.workers.dev` |
| `BEOPSUNY_BRIGHTDATA_USERNAME` | Bright Data 사용자명 | `brd-customer-xxx-zone-kr` |
| `BEOPSUNY_BRIGHTDATA_PASSWORD` | Bright Data 비밀번호 | `your-password` |
| `BEOPSUNY_FORCE_PROXY` | 강제 프록시 사용 | `1`, `true` |
| `BEOPSUNY_SKIP_GEO_CHECK` | 지역 체크 스킵 | `1`, `true` |

## 문제 해결

### "Cloudflare Worker URL not configured"

프록시 URL이 설정되지 않았습니다:
```bash
export BEOPSUNY_PROXY_URL='https://your-worker.workers.dev'
```

### "403 Forbidden"

1. 프록시가 올바르게 설정되었는지 확인
2. Cloudflare Worker가 배포되었는지 확인
3. Worker의 ALLOWED_DOMAINS에 도메인이 포함되어 있는지 확인

### "한국 IP가 아님"

프록시를 통해 접속했지만 한국 IP가 아닌 경우:
- Bright Data: Zone 설정에서 한국(KR) 선택
- Cloudflare: Worker가 한국 리전에서 실행되지 않을 수 있음 (일부 API는 작동)

### 국내에서 프록시 우회

국내에서 테스트하지만 프록시를 테스트하고 싶을 때:
```bash
export BEOPSUNY_FORCE_PROXY=1
```

## 보안 고려사항

1. **API 키 보호**: 프록시 URL을 공개하지 마세요
2. **Cloudflare Worker API 키**: 필요시 Worker에 API 키 인증 추가
3. **Bright Data 자격증명**: 환경변수로만 관리, 코드에 하드코딩 금지
