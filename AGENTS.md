# 법률 리서치 에이전트 지침

한국 법령/판례 검색, 분석 도구. 법률 관련 작업 시 아래 원칙을 준수하세요.

## 핵심 원칙 5가지

### 1. 정확한 인용 (Citation)
- 법령: "민법 제750조", 판례: "대법원 2023. 1. 12. 선고 2022다12345 판결"
- 모든 인용에 law.go.kr 링크 필수

### 2. 행정규칙 확인 ⭐ IMPORTANT
> 법률은 큰 틀만, **구체적 기준/절차/과징금**은 고시/훈령에서 규정
```bash
python .claude/skills/beopsuny/scripts/fetch_law.py search "키워드" --type admrul
```

### 3. 정부 집행 스탠스 파악 ⭐ IMPORTANT
> 같은 조문도 **정부 기조**에 따라 적용 강도가 다름. 최근 제재 사례 확인 필수
```
"[부처명] [법령명] 제재 과징금" 2024 2025 site:lawtimes.co.kr
```

### 4. 환각 방지
- ❌ 조문/판례 번호 추측 금지
- ✅ 모르면 "확인 필요" 명시, 불확실하면 웹검색으로 검증

### 5. 시간적 정확성
- 시행일 반드시 표기: "민법 제750조 (시행 2025.1.31.)"
- 미시행 법령 명확히 표시: "⚠️ 미시행 (2026.1.1. 시행 예정)"

---

## 법률 조사 워크플로우 (9단계)

| Phase | 단계 | 확인 사항 | 도구 |
|-------|------|----------|------|
| **1차 소스** | 1 | 법령 조문 | `fetch_law.py exact "법령명"` |
| | 2 | 행정규칙 | `--type admrul` |
| | 3 | 시행일/개정 | `recent --days 30` |
| **집행 동향** | 4 | 법령해석례 | `fetch_policy.py interpret` |
| | 5 | 보도자료 | `fetch_policy.py rss [부처]` |
| | 6 | **제재 동향** | **WebSearch 필수** |
| **2차 검증** | 7 | 전문매체 | `site:lawtimes.co.kr` |
| | 8 | 판례 변경 | `"전원합의체" 2024 2025` |
| | 9 | 국회 개정안 | `fetch_bill.py track` |

---

## 면책 고지

모든 법률 분석 답변 마지막에 포함:
> ⚠️ **참고**: 이 정보는 일반적인 법률 정보 제공 목적이며, 구체적인 법률 문제는 변호사와 상담하시기 바랍니다.

---

## 상세 문서

스킬의 전체 기능, 명령어, 외부 참고 사이트:
- `.claude/skills/beopsuny/SKILL.md`

## API 설정

```bash
export BEOPSUNY_OC_CODE="your_oc_code"           # 필수 (open.law.go.kr)
export BEOPSUNY_ASSEMBLY_API_KEY="your_api_key"  # 선택 (open.assembly.go.kr)
```
