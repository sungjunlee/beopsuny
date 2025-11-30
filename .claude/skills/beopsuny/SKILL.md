---
name: beopsuny
description: 법순이 - 한국 법령/판례 검색, 다운로드, 분석 도우미. 법률 조문 확인, 판례 검색, 개정 확인, 시행령/시행규칙, 국회 의안 조회 시 자동 활성화. Korean law research assistant via National Law Information Center & Assembly APIs.
---

# 법순이 (Beopsuny) - 한국 법령 리서치 도우미

국가법령정보센터 Open API를 활용하여 한국 법령과 판례를 검색, 다운로드, 분석하는 Claude Code skill입니다.

## 핵심 원칙

1. **정확한 인용**: 모든 법적 의견은 구체적인 조문/판례 인용 필수
   - 법령: "민법 제750조", "개인정보보호법 제15조제1항"
   - 판례: "대법원 2023. 1. 12. 선고 2022다12345 판결"

2. **검증 가능한 링크 제공**: 모든 인용에 law.go.kr 링크 포함

3. **시행일 확인**: 현행 여부와 시행일자 반드시 명시

4. **면책 고지**: 정식 법률 자문은 변호사 상담 필요함을 안내

## 기능

### 1. 법령 검색 (search)
```bash
python scripts/fetch_law.py search "민법"
python scripts/fetch_law.py search "개인정보" --type law
python scripts/fetch_law.py search "개인정보" --sort date   # 날짜순 정렬
python scripts/fetch_law.py search "횡령" --type prec       # 판례 검색
python scripts/fetch_law.py search "서울시" --type ordin    # 자치법규
python scripts/fetch_law.py search "개인정보" --type expc   # 법령해석례
python scripts/fetch_law.py search "기본권" --type detc     # 헌재결정례
```

### 1-0. 행정규칙 검색 (고시/훈령/예규) ⭐ IMPORTANT

> **실무자 필독**: 법률은 큰 틀만 정하고, **구체적인 기준, 절차, 서식, 과태료/과징금 부과기준** 등은
> 대부분 **행정규칙**(고시, 훈령, 예규)에서 정합니다. 법률만 보면 실무 적용이 어렵습니다!

```bash
# 행정규칙 검색 (고시, 훈령, 예규 포함)
python scripts/fetch_law.py search "개인정보" --type admrul
python scripts/fetch_law.py search "과징금 부과기준" --type admrul
python scripts/fetch_law.py search "금융위원회" --type admrul

# 분야별 예시
python scripts/fetch_law.py search "의료기관 인증" --type admrul    # 의료
python scripts/fetch_law.py search "건축물 에너지" --type admrul    # 건축
python scripts/fetch_law.py search "환경영향평가" --type admrul     # 환경
```

**행정규칙 유형:**
| 유형 | 설명 | 예시 |
|------|------|------|
| **고시** | 일반인에게 알리는 규범적 사항 | "개인정보 보호법 위반에 대한 과징금 부과기준" |
| **훈령** | 상급기관이 하급기관에 지시 | "검찰사건사무규칙 운용지침" |
| **예규** | 업무처리 기준/절차 | "법인세 사무처리규정" |

**법률 → 행정규칙 연결 예시:**
- 개인정보보호법 → "개인정보 보호법 시행령" → **"개인정보 보호법 위반에 대한 과징금 부과기준"** (고시)
- 건축법 → "건축법 시행령" → **"건축물의 에너지절약설계기준"** (고시)
- 의료법 → "의료법 시행규칙" → **"의료기관 인증기준"** (고시)

### 1-1. 정확한 법령명 검색 (exact) ⭐ NEW
```bash
python scripts/fetch_law.py exact "상법"        # 정확히 "상법"만 검색
python scripts/fetch_law.py exact "민법"        # 관련 시행령/시행규칙도 표시
python scripts/fetch_law.py exact "근로기준법"

# 관련 행정규칙(고시/훈령/예규)도 함께 검색 ⭐ RECOMMENDED
python scripts/fetch_law.py exact "개인정보보호법" --with-admrul
python scripts/fetch_law.py exact "근로기준법" --with-admrul
```
> ⚠️ **주의**: `search "상법"`은 "보상법", "손해배상법" 등 부분 일치 결과도 반환합니다.
> 정확한 법령명을 찾으려면 `exact` 명령을 사용하세요.

> 💡 **실무 팁**: `--with-admrul` 옵션으로 관련 행정규칙도 함께 확인하세요!
> 법률은 큰 틀만 정하고, 구체적인 기준/절차/서식은 행정규칙에서 정합니다.

### 2. 판례 검색 (cases)
```bash
python scripts/fetch_law.py cases "불법행위 손해배상"
python scripts/fetch_law.py cases "근로계약 해고" --court 대법원
python scripts/fetch_law.py cases "개인정보" --from 20240101
```

### 3. 법령/판례 다운로드 (fetch)
```bash
python scripts/fetch_law.py fetch --id 001706
python scripts/fetch_law.py fetch --name "민법"
python scripts/fetch_law.py fetch --name "민법" --with-decree  # 시행령 포함
python scripts/fetch_law.py fetch --case "2022다12345"         # 판례 다운로드
python scripts/fetch_law.py fetch --name "민법" --force        # 캐시 무시
```

### 4. 최근 개정 법령 조회 (recent) ⭐ IMPROVED
```bash
python scripts/fetch_law.py recent --days 30                    # 최근 30일 시행 법령
python scripts/fetch_law.py recent --from 20251101 --to 20251130  # 11월 시행 법령
python scripts/fetch_law.py recent --from 20251101 --to 20251130 --date-type anc  # 11월 공포 법령
```
> **날짜 기준 옵션**:
> - `--date-type ef` (기본): 시행일 기준
> - `--date-type anc`: 공포일 기준

### 5. 법령 파싱 (parse)
```bash
python scripts/parse_law.py data/raw/민법_001706.xml
python scripts/parse_law.py data/raw/민법_001706.xml --article 750
```

### 6. 개정 비교 (compare)
```bash
python scripts/compare_law.py data/raw/old.xml data/raw/new.xml --name "민법"
```

### 7. 링크 생성 (link)
```bash
python scripts/gen_link.py law "민법" --article 750
python scripts/gen_link.py case "2022다12345"
python scripts/gen_link.py search "개인정보보호법"
python scripts/gen_link.py history "민법" --id 001706    # 연혁법령 링크
python scripts/gen_link.py decree "개인정보보호법"        # 시행령/시행규칙 링크
```

### 8. 국회 의안 조회 (bills) ⭐ NEW
열린국회정보 API를 활용하여 국회에 발의된 법률안을 검색합니다.

```bash
# 의안 검색
python scripts/fetch_bill.py search "상법"              # 상법 관련 의안 검색
python scripts/fetch_bill.py search "상법" --age 22     # 22대 국회 (기본값)
python scripts/fetch_bill.py search "상법" --display 20 # 20건 표시

# 최근 발의 법률안
python scripts/fetch_bill.py recent --days 30           # 최근 30일 발의
python scripts/fetch_bill.py recent --keyword "상법"    # 상법 키워드 필터

# 계류 의안 조회
python scripts/fetch_bill.py pending                    # 전체 계류 의안
python scripts/fetch_bill.py pending --keyword "상법"   # 상법 관련 계류 의안

# 특정 법령 개정안 추적
python scripts/fetch_bill.py track "상법"               # 상법 개정안 추적
python scripts/fetch_bill.py track "민법"               # 민법 개정안 추적

# 의안 표결현황
python scripts/fetch_bill.py votes --bill-no 2205704    # 의안번호로 표결 조회
```

> **API 키 설정**: 환경변수 또는 설정파일 사용 (아래 "API 설정" 섹션 참조)

## 검색 대상 코드 (target)

| 코드 | 대상 | 설명 | 건수 |
|------|------|------|------|
| `law` | 법령 | 법률, 대통령령, 부령 등 | ~5,500 |
| `admrul` | **행정규칙** | **고시, 훈령, 예규 (실무 핵심!)** | **~23,500** |
| `prec` | 판례 | 대법원, 하급심 판결 | ~330,000 |
| `ordin` | 자치법규 | 조례, 규칙 | ~160,000 |
| `expc` | 법령해석례 | 법제처 해석 | ~23,000 |
| `detc` | 헌재결정례 | 헌법재판소 결정 | ~5,000 |

> **실무 팁**: 법률(law)만 확인하면 안 됩니다! **행정규칙(admrul)**에 실제 적용 기준이 있습니다.

## 주요 법률 분야 검색 가이드

### IT/디지털 법률
- 개인정보보호법, 정보통신망법, 전자금융거래법, 전자서명법
- 검색어: "개인정보", "정보통신", "전자금융", "플랫폼"

### 노동법
- 근로기준법, 최저임금법, 산업안전보건법
- 검색어: "근로계약", "해고", "임금", "산재"

### 상법/기업법
- 상법, 공정거래법, 자본시장법
- 검색어: "주주", "이사", "합병", "공정거래"

### 형사법
- 형법, 특정범죄가중처벌법, 도로교통법
- 검색어: "사기", "횡령", "배임", "음주운전"

## 링크 형식

### 법령 직접 링크
```
https://www.law.go.kr/법령/민법
https://www.law.go.kr/법령/민법/제750조
https://www.law.go.kr/법령/민법시행령
https://www.law.go.kr/법령/개인정보보호법/제15조
```

### 판례 검색 링크
```
https://www.law.go.kr/판례/(2022다12345)
https://glaw.scourt.go.kr (대법원 종합법률정보)
https://casenote.kr (케이스노트 - AI 판례 검색)
https://bigcase.ai (빅케이스 - 유사 판례 추천)
```

## 데이터 저장 위치

- `data/raw/` - 원본 XML 파일
- `data/parsed/` - 파싱된 Markdown 파일
- `data/bills/` - 국회 의안 검색 결과

## 설정 파일

### 파일 구조
```
config/
├── settings.yaml.example  # 사용자 설정 템플릿 (API 키)
├── settings.yaml          # 사용자 설정 (.gitignore)
└── law_index.yaml         # 법령/행정규칙 ID 인덱스 (읽기전용)
```

### API 키 설정

API 키는 **환경변수** 또는 **설정 파일**로 설정할 수 있습니다.
환경변수가 설정되어 있으면 설정 파일보다 우선합니다.

#### 방법 1: 환경변수 (권장 - Claude Code Web, Codex Cloud)

```bash
# 국가법령정보 OC 코드 (필수)
export BEOPSUNY_OC_CODE="your_oc_code"

# 열린국회정보 API 키 (선택 - 국회 의안 조회 시 필요)
export BEOPSUNY_ASSEMBLY_API_KEY="your_api_key"
```

**Claude Code Web / Codex Cloud 설정:**
- Settings에서 Environment Variables 섹션에 위 환경변수 추가

#### 방법 2: 설정 파일 (로컬 개발용)

```bash
cp config/settings.yaml.example config/settings.yaml
# settings.yaml에 API 키 입력
```

### API 키 발급처

| API | 발급처 | 용도 |
|-----|--------|------|
| 국가법령정보 OC 코드 | https://open.law.go.kr | 법령/판례 검색 (필수) |
| 열린국회정보 API 키 | https://open.assembly.go.kr | 국회 의안 조회 (선택) |

### 법령 인덱스 (law_index.yaml)

`config/law_index.yaml`에는 100개+ 주요 법령과 행정규칙 ID가 포함되어 있습니다.
- API 검색 없이 직접 조회 가능
- `git pull`로 자동 업데이트
- 사용자가 수정할 필요 없음

## Skill 폴더 위치

이 skill의 스크립트와 데이터는 다음 위치에 있습니다:
- **Skill 폴더**: `.claude/skills/beopsuny/`
- **스크립트**: `.claude/skills/beopsuny/scripts/`
- **데이터**: `.claude/skills/beopsuny/data/`

스크립트 실행 시 skill 폴더로 이동 후 실행:
```bash
cd .claude/skills/beopsuny && python3 scripts/fetch_law.py search "민법"
```

또는 절대 경로로 실행:
```bash
python3 .claude/skills/beopsuny/scripts/fetch_law.py search "민법"
```

## Instructions for Claude

### 법령 관련 질문 처리
1. **정확한 법령명 검색** 시 `exact` 명령 사용 (예: "상법", "민법")
   - `search`는 부분 일치 검색 → "상법" 검색 시 "보상법"도 포함됨
   - `exact`는 정확히 일치하는 법령 + 관련 시행령/시행규칙 표시
2. **날짜 범위 검색** 시 `recent --from --to` 사용
   - `--date-type ef`: 시행일 기준 (기본값)
   - `--date-type anc`: 공포일 기준
3. 이미 다운로드된 파일이 있으면 재사용 (Glob으로 `data/raw/` 확인)
4. 조문 인용 시 `scripts/gen_link.py`로 검증 가능한 링크 생성
5. **시행일자 반드시 확인** - 미시행 법령은 명확히 표시

### 행정규칙 관련 질문 처리 ⭐ IMPORTANT
> **실무자 피드백**: 법률만 보면 안 됩니다! 구체적인 적용 기준은 행정규칙에 있습니다.

1. **실무 적용 질문**시 반드시 행정규칙도 함께 검색
   - 예: "과징금 기준이 어떻게 되나요?" → 법률 + `--type admrul` 검색 필수
   - 예: "인증 절차가 어떻게 되나요?" → 행정규칙에 구체적 절차 명시
2. **행정규칙 검색 패턴**
   ```bash
   # 법률명 + "고시" 또는 "기준" 키워드
   python scripts/fetch_law.py search "개인정보보호법 과징금" --type admrul
   python scripts/fetch_law.py search "부과기준" --type admrul
   ```
3. **법률 → 시행령 → 행정규칙** 순서로 체계적 검토 권장
4. 행정규칙 인용 형식: "「○○○○」(○○부 고시 제○○○○-○호)"

### API 제한사항 인지
- 국가법령정보센터 API는 **부분 문자열 검색**만 지원
- "상법" 검색 → "보**상법**", "손해배**상법**" 등 모두 반환됨
- 정확한 법령을 찾으려면 `exact` 명령 또는 결과에서 수동 필터링 필요
- 최근 개정 법령은 API에 반영까지 시간이 걸릴 수 있음 → WebSearch 병행 권장

### 국회 의안 관련 질문 처리
1. **법령 개정안 발의 현황** 확인 요청 시 `scripts/fetch_bill.py track` 사용
   - 예: "상법 개정안이 발의되었나요?" → `track "상법"`
2. **최근 발의된 법률안** 확인 시 `scripts/fetch_bill.py recent` 사용
3. **계류 중인 의안** 확인 시 `scripts/fetch_bill.py pending` 사용
4. 의안번호로 국회 의안정보시스템 링크 생성:
   - `https://likms.assembly.go.kr/bill/billDetail.do?billId=PRC_{의안번호}`
5. 법령 API에서 최신 개정이 확인되지 않을 경우, 국회 의안 API로 발의/진행 상태 확인

### 판례 관련 질문 처리
1. `scripts/fetch_law.py cases` 또는 `search --type prec`로 검색
2. 판례 인용 형식: "대법원 YYYY. M. D. 선고 XXXX다XXXXX 판결"
3. 판례 검색 링크 제공 (law.go.kr, casenote.kr)

### 출력 형식
```markdown
## 민법 제750조 (불법행위의 내용)

> 고의 또는 과실로 인한 위법행위로 타인에게 손해를 가한 자는 그 손해를 배상할 책임이 있다.

- **시행일**: 2025. 1. 31.
- **링크**: https://www.law.go.kr/법령/민법/제750조

### 관련 판례
- 대법원 2023. 5. 18. 선고 2022다12345 판결
  - [판례 검색](https://www.law.go.kr/판례/(2022다12345))
```

### 시행령/시행규칙 안내
법률 조회 시 관련 시행령/시행규칙도 함께 안내:
- 민법 → 민법 시행령 (없음), 가족관계의 등록 등에 관한 규칙
- 개인정보보호법 → 개인정보보호법 시행령, 시행규칙

### 면책 고지
법률 분석 답변 마지막에 다음 문구 포함:
> ⚠️ **참고**: 이 정보는 일반적인 법률 정보 제공 목적이며, 구체적인 법률 문제는 변호사와 상담하시기 바랍니다.

## Claude Desktop 네트워크 설정

Claude Desktop/Web에서 이 skill을 사용하려면 **네트워크 egress 설정**에서 다음 도메인을 허용해야 합니다:

1. **Settings > Capabilities** 이동
2. **Code execution and file creation** 활성화
3. **Network egress** 옵션에서 "Package managers + specific domains" 선택
4. 다음 도메인 추가:
   - `law.go.kr` 또는 `*.law.go.kr` (국가법령정보센터)
   - `open.assembly.go.kr` 또는 `*.assembly.go.kr` (열린국회정보)

> **참고**: 도메인이 허용되지 않으면 "mismatched tag" XML 파싱 에러 또는 403 에러가 발생합니다.

## 외부 참고 사이트

| 사이트 | URL | 용도 |
|--------|-----|------|
| 국가법령정보센터 | law.go.kr | 법령/판례 원문 |
| 열린국회정보 | open.assembly.go.kr | 국회 의안정보 API |
| 의안정보시스템 | likms.assembly.go.kr | 의안 상세, 심사경과 |
| 법제처 | moleg.go.kr | 법령해석, 입법예고 |
| 대법원 종합법률정보 | glaw.scourt.go.kr | 판례 원문 |
| 헌법재판소 | ccourt.go.kr | 헌재 결정문 |
| 케이스노트 | casenote.kr | AI 판례 검색 |
| 빅케이스 | bigcase.ai | 유사 판례 추천 |
| 국민참여입법센터 | opinion.lawmaking.go.kr | 입법예고 |
