# 법률 리서치 에이전트 지침

이 프로젝트는 한국 법령/판례를 검색, 분석하는 도구를 제공합니다.
법률 관련 작업 시 다음 원칙을 준수하세요.

## 1. 출처 정확성 (Citation Accuracy)

### 필수 인용 형식
- **법령**: "민법 제750조", "개인정보보호법 제15조제1항"
- **판례**: "대법원 2023. 1. 12. 선고 2022다12345 판결"
- **참고**: [법률문헌의 인용방법 표준안](https://namu.wiki/w/법률문헌의%20인용방법%20표준안) (사법정책연구원, 2017)

### 링크 필수 제공
모든 인용에 검증 가능한 링크 포함:
- 법령: `https://www.law.go.kr/법령/민법/제750조`
- 판례: `https://www.law.go.kr/판례/(2022다12345)`

## 2. 교차 검증 (Cross-Verification)

### 반드시 확인할 사항
- [ ] 해당 조문이 **현행법**인지 (시행일 확인)
- [ ] **개정 여부** 확인 (최근 개정이 있었는지)
- [ ] 판례의 경우 **폐기/변경 여부** 확인

### 검증 방법
1. `fetch_law.py`로 다운로드한 법령의 시행일 확인
2. `recent` 명령으로 최근 개정 여부 확인
3. 가능하면 **복수의 출처**로 교차 확인 (law.go.kr + 판례 검색 사이트)

## 3. 행정규칙 확인 (Administrative Rules) ⭐ IMPORTANT

### 실무자 피드백
> "법률이 바뀌는 것도 중요하지만, 실제로 적용되는 부분은 **고시, 훈령, 예규**에서 정하는 경우가 많습니다."

### 필수 확인 사항
- ✅ 구체적인 **기준/절차/서식**은 행정규칙 검색 필수
- ✅ **과징금/과태료 부과기준**은 대부분 고시에서 규정
- ✅ 법률 → 시행령 → **행정규칙** 순서로 체계적 확인

### 검색 방법
```bash
# 행정규칙 검색 (고시, 훈령, 예규)
python .claude/skills/beopsuny/scripts/fetch_law.py search "과징금 부과기준" --type admrul
python .claude/skills/beopsuny/scripts/fetch_law.py search "인증기준" --type admrul
```

## 4. 정부 정책 집행 스탠스 파악 ⭐ IMPORTANT

### 실무자 피드백
> "법령 조문보다 **정부의 실제 집행 스탠스**가 실무에 더 중요합니다.
> 공정거래위원회, 고용노동부, 금융위원회 등의 최근 제재 동향을 파악해야 합니다."

### 왜 중요한가?
- 같은 법 조문이라도 **정부 기조**에 따라 적용 강도가 달라짐
- 최근 **제재 사례**를 보면 현 정부의 집행 방향 파악 가능
- 법률 자문 시 "현재 분위기"를 아는 것이 핵심

### 주요 조사 대상 기관

| 기관 | 관련 법령 | RSS 피드 |
|------|----------|----------|
| 공정거래위원회 | 공정거래법, 하도급법, 가맹사업법 | https://korea.kr/rss/dept_ftc.xml |
| 고용노동부 | 근로기준법, 산업안전보건법 | https://korea.kr/rss/dept_moel.xml |
| 금융위원회 | 자본시장법, 금융소비자보호법 | https://korea.kr/rss/dept_fsc.xml |
| 개인정보보호위원회 | 개인정보보호법 | https://korea.kr/rss/dept_pipc.xml |

### 조사 방법

#### 1. 웹검색 활용 (즉시 적용)
```
# 최근 제재 동향
"공정거래위원회 제재" 2024 2025
"고용노동부 근로기준법 위반" 과태료 2024
"금융위원회 제재조치" 최근

# 정책 기조
공정거래위원회 정책 방향 2025
고용노동부 노동정책 기조
```

#### 2. 보도자료 RSS 확인
- 정책브리핑(korea.kr)에서 각 부처 RSS 피드 제공
- 최근 보도자료로 정책 방향 파악

#### 3. 공개 API 활용 (심층 조사)

| 데이터 | API (data.go.kr) | 용도 |
|--------|------------------|------|
| 공정위 의결서 | /data/15103301 | 실제 제재 결정문 |
| 고용노동부 행정해석 | /data/15140236 | 법령 해석 사례 |
| 입법예고 | /data/15058407 | 법령 개정 동향 |

### 실무 적용 예시

**질문**: "하도급법 위반 시 과징금 수준이 어느 정도인가요?"

**조사 순서**:
1. 하도급법 과징금 조항 확인 (법령 검색)
2. 하도급법 과징금 부과기준 고시 확인 (행정규칙 검색)
3. **최근 공정위 제재 사례 검색** (웹검색/보도자료)
4. 실제 부과된 과징금 규모와 동향 파악

---

## 5. 환각 방지 (Hallucination Prevention)

### 금지 사항
- ❌ 조문 번호나 내용을 **추측**하지 말 것
- ❌ 판례 번호를 **생성**하지 말 것
- ❌ 존재하지 않는 법령을 **언급**하지 말 것

### 필수 사항
- ✅ 모르면 **"확인 필요"**라고 명시
- ✅ API 검색 결과가 없으면 **"검색 결과 없음"** 명시
- ✅ 불확실한 정보는 **웹검색으로 추가 검증**

## 6. 시간적 정확성 (Temporal Accuracy)

### 시행일 명시
- 모든 법령 인용 시 시행일 표기: "민법 제750조 (시행 2025.1.31.)"
- **미시행 법령**은 반드시 표시: "⚠️ 미시행 (2026.1.1. 시행 예정)"

### 개정 추적
- 법령 개정안이 국회 계류 중인지 `fetch_bill.py`로 확인
- 최근 공포되었으나 미시행인 개정 사항 안내

## 7. 면책 고지 (Disclaimer)

모든 법률 분석 답변 마지막에 포함:

> ⚠️ **참고**: 이 정보는 일반적인 법률 정보 제공 목적이며,
> 구체적인 법률 문제는 변호사와 상담하시기 바랍니다.

---

## 도구 사용법

법률 조사 시 `.claude/skills/beopsuny/` 스킬을 활용하세요.

### 법령 검색
```bash
# 정확한 법령명 검색 (부분 일치 방지)
python .claude/skills/beopsuny/scripts/fetch_law.py exact "상법"

# 키워드 검색
python .claude/skills/beopsuny/scripts/fetch_law.py search "개인정보" --type law

# 법령 다운로드
python .claude/skills/beopsuny/scripts/fetch_law.py fetch --name "민법"
```

### 판례 검색
```bash
# 판례 검색
python .claude/skills/beopsuny/scripts/fetch_law.py cases "불법행위 손해배상"

# 특정 법원 판례
python .claude/skills/beopsuny/scripts/fetch_law.py cases "해고" --court 대법원
```

### 행정규칙 검색 (고시/훈령/예규) ⭐ IMPORTANT
```bash
# 행정규칙 검색 - 실무 적용 기준 확인 필수!
python .claude/skills/beopsuny/scripts/fetch_law.py search "과징금 부과기준" --type admrul
python .claude/skills/beopsuny/scripts/fetch_law.py search "개인정보" --type admrul
python .claude/skills/beopsuny/scripts/fetch_law.py search "금융위원회" --type admrul
```
> 법률은 큰 틀만 정하고, 구체적인 **기준/절차/서식**은 행정규칙에서 정합니다.

### 개정 확인
```bash
# 최근 시행 법령
python .claude/skills/beopsuny/scripts/fetch_law.py recent --days 30

# 특정 기간 공포 법령
python .claude/skills/beopsuny/scripts/fetch_law.py recent --from 20251101 --to 20251130 --date-type anc
```

### 국회 의안 조회
```bash
# 법령 개정안 추적
python .claude/skills/beopsuny/scripts/fetch_bill.py track "상법"

# 계류 중인 의안
python .claude/skills/beopsuny/scripts/fetch_bill.py pending --keyword "민법"

# 최근 발의 법안
python .claude/skills/beopsuny/scripts/fetch_bill.py recent --days 30
```

### 링크 생성
```bash
# 법령 링크
python .claude/skills/beopsuny/scripts/gen_link.py law "민법" --article 750

# 판례 링크
python .claude/skills/beopsuny/scripts/gen_link.py case "2022다12345"
```

---

## 상세 문서

도구의 전체 사용법과 옵션은 다음 파일을 참조하세요:
- `.claude/skills/beopsuny/SKILL.md`

## API 설정

스킬 사용 전 API 키 설정이 필요합니다. **환경변수** 또는 **설정 파일** 사용 가능.

### 환경변수 (권장 - Claude Code Web, Codex Cloud)
```bash
export BEOPSUNY_OC_CODE="your_oc_code"           # 필수
export BEOPSUNY_ASSEMBLY_API_KEY="your_api_key"  # 선택
```

### 설정 파일 (로컬)
`.claude/skills/beopsuny/config/settings.yaml`

### API 키 발급
- **국가법령정보 OC 코드**: https://open.law.go.kr (필수)
- **열린국회정보 API 키**: https://open.assembly.go.kr (선택)

## 외부 참고 사이트

| 사이트 | URL | 용도 |
|--------|-----|------|
| 국가법령정보센터 | https://law.go.kr | 법령/판례 원문 |
| 대법원 종합법률정보 | https://glaw.scourt.go.kr | 판례 원문 |
| 헌법재판소 | https://ccourt.go.kr | 헌재 결정문 |
| 국회 의안정보시스템 | https://likms.assembly.go.kr | 의안 상세 |
| 케이스노트 | https://casenote.kr | AI 판례 검색 |
| 빅케이스 | https://bigcase.ai | 유사 판례 추천 |
