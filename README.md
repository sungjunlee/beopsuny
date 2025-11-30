# 법순이 (Beopsuny) - 한국 법령 리서치 AI Agent Skill

한국 법령/판례를 검색, 다운로드, 분석하는 AI Agent Skill 템플릿입니다.

**Claude Code, OpenAI Codex, Gemini CLI, Cursor** 등 다양한 AI 도구에서 사용할 수 있습니다.

## ✨ 주요 기능

- **법령 검색**: 법률, 시행령, 시행규칙 검색 및 다운로드
- **행정규칙 검색**: 고시, 훈령, 예규 등 실무 적용 규정 조회 (~23,500건)
- **판례 검색**: 대법원/하급심 판례 검색 및 본문 조회
- **국회 의안 조회**: 발의된 법률안 검색, 개정안 추적, 표결 현황
- **다양한 법령 유형**: 자치법규, 법령해석례, 헌재결정례
- **링크 생성**: law.go.kr 직접 링크 자동 생성

## 🚀 빠른 시작

### 1. 템플릿에서 레포지토리 생성

GitHub에서 **"Use this template"** 버튼을 클릭하여 새 레포지토리를 생성합니다.

### 2. API 키 설정

#### 방법 A: 환경변수 (권장 - Claude Code Web, Codex Cloud)

```bash
# 국가법령정보 OC 코드 (필수)
export BEOPSUNY_OC_CODE="your_oc_code"

# 열린국회정보 API 키 (선택 - 국회 의안 조회용)
export BEOPSUNY_ASSEMBLY_API_KEY="your_api_key"
```

#### 방법 B: 설정 파일 (로컬 개발용)

```bash
cp .claude/skills/beopsuny/config/settings.yaml.example \
   .claude/skills/beopsuny/config/settings.yaml
# settings.yaml에 API 키 입력
```

### 3. API 키 발급

| API | 발급처 | 용도 |
|-----|--------|------|
| 국가법령정보 OC 코드 | https://open.law.go.kr | 법령/판례 검색 (필수) |
| 열린국회정보 API 키 | https://open.assembly.go.kr | 국회 의안 조회 (선택) |

> **OC 코드**: 가입한 이메일의 @ 앞부분입니다. (예: `user@gmail.com` → `user`)

## 📖 사용법

### 법령 검색

```bash
# 정확한 법령명 검색
python scripts/fetch_law.py exact "상법"

# 키워드 검색
python scripts/fetch_law.py search "개인정보" --type law

# 판례 검색
python scripts/fetch_law.py cases "불법행위 손해배상"
```

### 행정규칙 검색 (고시/훈령/예규)

> 실무에서는 법률보다 **행정규칙**(고시, 훈령, 예규)이 더 중요할 수 있습니다.
> 법률은 큰 틀만 정하고, 구체적인 기준과 절차는 행정규칙에서 정하는 경우가 많습니다.

```bash
# 행정규칙 검색
python scripts/fetch_law.py search "개인정보" --type admrul

# 부처별 행정규칙
python scripts/fetch_law.py search "금융위원회" --type admrul

# 특정 분야 고시/예규
python scripts/fetch_law.py search "과징금 부과기준" --type admrul
```

**주요 행정규칙 예시:**
- 개인정보 처리방침 → "개인정보 보호법 위반에 대한 과징금 부과기준" (고시)
- 금융규제 → "금융회사의 정보처리 및 전산설비 위탁에 관한 규정" (고시)

### 정책 동향 파악 ⭐ NEW

> 법령 조문보다 **정부의 실제 집행 스탠스**가 실무에 더 중요합니다.

```bash
# 부처별 보도자료 수집
python scripts/fetch_policy.py rss ftc                   # 공정거래위원회
python scripts/fetch_policy.py rss moel --keyword 임금   # 고용노동부 + 필터

# 법령해석례 검색
python scripts/fetch_policy.py interpret "해고"

# 정책 동향 종합 요약
python scripts/fetch_policy.py summary --days 7
```

### 국회 의안 조회

```bash
# 법률 개정안 추적
python scripts/fetch_bill.py track "상법"

# 최근 발의된 법률안
python scripts/fetch_bill.py recent --days 30

# 계류 중인 의안
python scripts/fetch_bill.py pending --keyword "민법"
```

### 법령 다운로드

```bash
python scripts/fetch_law.py fetch --name "민법"
python scripts/fetch_law.py fetch --case "2022다12345"
```

### 링크 생성

```bash
python scripts/gen_link.py law "민법" --article 750
python scripts/gen_link.py case "2022다12345"
```

## 🤖 AI 도구별 사용법

### Claude Code (CLI/Web)

```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo
# CLAUDE.md가 자동으로 로드됨
```

### OpenAI Codex

```bash
git clone https://github.com/your-username/your-repo.git
# AGENTS.md가 자동으로 로드됨
```

### Gemini CLI

```bash
git clone https://github.com/your-username/your-repo.git
# AGENTS.md가 자동으로 로드됨
```

### Cursor

프로젝트를 열면 AGENTS.md가 자동으로 인식됩니다.

## 📁 프로젝트 구조

```
.
├── AGENTS.md                    # AI 에이전트 지침 (Codex, Gemini, Cursor)
├── CLAUDE.md -> AGENTS.md       # Claude Code용 (symlink)
├── .claude/skills/beopsuny/
│   ├── SKILL.md                 # 상세 사용법
│   ├── scripts/
│   │   ├── fetch_law.py         # 법령/판례 검색
│   │   ├── fetch_bill.py        # 국회 의안 조회
│   │   ├── fetch_policy.py      # 정책 동향 수집 ⭐ NEW
│   │   ├── parse_law.py         # 법령 파싱
│   │   └── gen_link.py          # 링크 생성
│   ├── config/
│   │   ├── settings.yaml.example  # API 키 설정 템플릿
│   │   └── law_index.yaml         # 법령 ID 인덱스 (자동 업데이트)
│   └── data/
│       ├── raw/                 # 다운로드된 XML
│       ├── parsed/              # 파싱된 Markdown
│       └── bills/               # 의안 검색 결과
├── build_skill.py               # Claude Desktop 빌드 스크립트
└── README.md
```

## 🔍 검색 대상

| 코드 | 대상 | 설명 | 건수 |
|------|------|------|------|
| `law` | 법령 | 법률, 대통령령, 부령 | ~5,500 |
| `admrul` | **행정규칙** | **고시, 훈령, 예규 (실무 핵심!)** | **~23,500** |
| `prec` | 판례 | 대법원, 하급심 판결 | ~330,000 |
| `ordin` | 자치법규 | 조례, 규칙 | ~160,000 |
| `expc` | 법령해석례 | 법제처 해석 | ~23,000 |
| `detc` | 헌재결정례 | 헌법재판소 결정 | ~5,000 |

> **실무 팁**: 법률만 확인하면 안 됩니다! 구체적인 기준, 절차, 서식은 대부분 **행정규칙**(고시/훈령/예규)에서 정합니다.

## ⚖️ 법률 리서치 원칙

이 템플릿을 사용하는 AI 에이전트는 다음 원칙을 따릅니다:

1. **정확한 인용**: 구체적인 조문/판례 번호 명시
2. **검증 가능한 링크**: law.go.kr 직접 링크 제공
3. **시행일 확인**: 현행 여부와 시행일자 표시
4. **교차 검증**: 가능하면 복수 출처 확인
5. **환각 방지**: 추측하지 않고, 모르면 "확인 필요" 명시
6. **면책 고지**: 정식 법률 자문은 변호사 상담 필요

## 🔗 참고 사이트

| 사이트 | URL | 용도 |
|--------|-----|------|
| 국가법령정보센터 | https://law.go.kr | 법령/판례 원문 |
| 열린국회정보 | https://open.assembly.go.kr | 국회 의안 API |
| 대법원 종합법률정보 | https://glaw.scourt.go.kr | 판례 원문 |
| 헌법재판소 | https://ccourt.go.kr | 헌재 결정문 |
| 케이스노트 | https://casenote.kr | AI 판례 검색 |
| 빅케이스 | https://bigcase.ai | 유사 판례 추천 |

## 📦 Claude Desktop 설치

로컬에서 Claude Desktop용 skill zip을 빌드하려면:

```bash
python build_skill.py
```

생성된 `beopsuny-skill.zip`을 Claude Desktop의 Skills 메뉴에서 추가합니다.

> ⚠️ zip 파일에는 개인 API 키가 포함되므로 공유하지 마세요.

## 📄 라이선스

MIT License
