---
name: beopsuny
description: 법순이 - 한국 법령/판례 검색, 다운로드, 분석 도우미. 법률 조문 확인, 판례 검색, 개정 확인, 시행령/시행규칙, 국회 의안 조회 시 자동 활성화. Korean law research assistant via National Law Information Center & Assembly APIs.
---

# 법순이 (Beopsuny) - 한국 법령 리서치 도우미

국가법령정보센터 Open API를 활용한 한국 법령/판례 검색, 분석 스킬.

## 핵심 원칙 (처음에 배치 - 중요)

1. **정확한 인용**: 법령 "민법 제750조", 판례 "대법원 2023. 1. 12. 선고 2022다12345 판결"
2. **law.go.kr 링크 필수**: 모든 인용에 검증 가능한 링크 포함
3. **시행일 확인**: 현행 여부, 미시행 법령 명시
4. **행정규칙 확인** ⭐: 구체적 기준/절차/과징금은 고시/훈령에서 규정
5. **면책 고지**: 정식 법률 자문은 변호사 상담 안내

---

## 필수 명령어 (자주 사용)

| 용도 | 명령어 |
|------|--------|
| 정확한 법령 검색 | `fetch_law.py exact "상법"` |
| 행정규칙 검색 ⭐ | `fetch_law.py search "과징금" --type admrul` |
| 판례 검색 | `fetch_law.py cases "해고" --court 대법원` |
| 최근 개정 | `fetch_law.py recent --days 30` |
| 국회 의안 | `fetch_bill.py track "상법"` |
| 정책 동향 | `fetch_policy.py rss ftc --keyword 과징금` |

> 스크립트 경로: `.claude/skills/beopsuny/scripts/`

---

## 검색 대상 코드

| 코드 | 대상 | 설명 |
|------|------|------|
| `law` | 법령 | 법률, 대통령령, 부령 |
| `admrul` | **행정규칙** ⭐ | 고시, 훈령, 예규 (실무 핵심) |
| `prec` | 판례 | 대법원, 하급심 |
| `ordin` | 자치법규 | 조례, 규칙 |
| `expc` | 법령해석례 | 법제처 해석 |
| `detc` | 헌재결정례 | 헌법재판소 결정 |

---

## 기능별 명령어

### 법령 검색
```bash
fetch_law.py exact "상법"                    # 정확한 법령명
fetch_law.py exact "상법" --with-admrul      # + 관련 행정규칙
fetch_law.py search "개인정보" --type law    # 키워드 검색
fetch_law.py search "과징금" --type admrul   # 행정규칙 검색
```

### 판례 검색
```bash
fetch_law.py cases "손해배상"
fetch_law.py cases "해고" --court 대법원 --from 20240101
```

### 법령 다운로드
```bash
fetch_law.py fetch --name "민법"
fetch_law.py fetch --name "민법" --with-decree  # 시행령 포함
fetch_law.py fetch --case "2022다12345"         # 판례
```

### 개정 확인
```bash
fetch_law.py recent --days 30                           # 최근 시행
fetch_law.py recent --from 20251101 --to 20251130       # 기간 지정
fetch_law.py recent --from 20251101 --date-type anc     # 공포일 기준
```

### 국회 의안
```bash
fetch_bill.py track "상법"           # 개정안 추적
fetch_bill.py pending --keyword 민법  # 계류 의안
fetch_bill.py recent --days 30       # 최근 발의
```

### 정책 동향
```bash
fetch_policy.py rss ftc --keyword 과징금   # 공정위 보도자료
fetch_policy.py interpret "해고"          # 법령해석례
fetch_policy.py summary --days 7          # 종합 요약
```

### 링크 생성
```bash
gen_link.py law "민법" --article 750
gen_link.py case "2022다12345"
```

---

## 정부 집행 스탠스 파악 ⭐ IMPORTANT

> 법령 조문보다 **정부의 실제 집행 스탠스**가 실무에 더 중요

### 주요 기관 RSS

| 기관 | 코드 | 관련 법령 |
|------|------|----------|
| 공정거래위원회 | `ftc` | 공정거래법, 하도급법 |
| 고용노동부 | `moel` | 근로기준법, 산업안전보건법 |
| 금융위원회 | `fsc` | 자본시장법 |
| 개인정보보호위원회 | `pipc` | 개인정보보호법 |

### 웹검색 패턴
```
"[부처명] [법령명] 과징금 제재" 2024 2025
"[키워드]" site:lawtimes.co.kr
"[키워드] 법제처 유권해석"
"[키워드] 대법원 전원합의체"
```

---

## API 설정

```bash
# 필수
export BEOPSUNY_OC_CODE="your_oc_code"           # open.law.go.kr

# 선택
export BEOPSUNY_ASSEMBLY_API_KEY="your_api_key"  # open.assembly.go.kr
```

또는 `config/settings.yaml`에 설정.

### 해외 접근 (게이트웨이)
```bash
export BEOPSUNY_GATEWAY_URL='https://your-gateway.example.com'
export BEOPSUNY_GATEWAY_API_KEY='your-api-key'
```

---

## 외부 참고 사이트

### 1차 소스 (공식)

| 사이트 | URL |
|--------|-----|
| 국가법령정보센터 | law.go.kr |
| 대법원 종합법률정보 | glaw.scourt.go.kr |
| 법제처 | moleg.go.kr |
| 의안정보시스템 | likms.assembly.go.kr |
| 국민참여입법센터 | opinion.lawmaking.go.kr |

### 2차 소스 (뉴스/전문매체)

| 사이트 | URL | 특징 |
|--------|-----|------|
| 법률신문 | lawtimes.co.kr | 판례 분석, 전문가 기고 |
| 월간노동법률 | worklaw.co.kr | 노동법 전문 |
| 로앤비 | lawnb.com | 법률정보, 판례 비교 |

### AI 법률 검색

| 사이트 | URL |
|--------|-----|
| 케이스노트 | casenote.kr |
| 빅케이스 | bigcase.ai |
| 엘박스 AI | lbox.kr |

---

## Instructions for Claude (끝에 배치 - recall 강화)

### 법령 검색 시
1. `exact` 사용 (search는 부분 일치 → "상법" 검색 시 "보상법" 포함)
2. 시행일 반드시 확인, 미시행 법령 명확히 표시
3. 이미 다운로드된 파일 있으면 재사용 (`data/raw/` 확인)

### 행정규칙 ⭐ IMPORTANT
> 법률만 보면 안 됩니다! 구체적 기준/절차/과징금은 행정규칙에 있습니다.

- 실무 질문 시 `--type admrul` 검색 필수
- 법률 → 시행령 → 행정규칙 순서로 체계적 검토

### 출력 형식
```markdown
## 민법 제750조 (불법행위의 내용)
> 고의 또는 과실로 인한 위법행위로 타인에게 손해를 가한 자는...

- **시행일**: 2025. 1. 31.
- **링크**: https://www.law.go.kr/법령/민법/제750조
```

### 면책 고지 (답변 마지막에 필수)
> ⚠️ **참고**: 이 정보는 일반적인 법률 정보 제공 목적이며, 구체적인 법률 문제는 변호사와 상담하시기 바랍니다.
