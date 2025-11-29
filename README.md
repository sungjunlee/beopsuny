# Beopsuny (법수니)

한국 법령 리서치를 도와주는 Claude skill입니다.

국가법령정보센터 Open API를 활용하여 법령, 판례, 행정규칙, 자치법규 등을 검색하고 분석합니다.

## 주요 기능

- **법령 검색**: 법률, 시행령, 시행규칙 검색 및 다운로드
- **판례 검색**: 대법원/하급심 판례 검색 및 본문 조회
- **다양한 법령 유형**: 행정규칙, 자치법규, 법령해석례, 헌재결정례
- **링크 생성**: law.go.kr 직접 링크 자동 생성
- **개정 비교**: 법령 개정 전후 비교

## 설치

### 방법 1: Claude Desktop용 (권장)

빌드 스크립트로 개인 설정이 포함된 zip 파일을 생성합니다.

**macOS/Linux:**
```bash
./build.sh
```

**Windows:**
```
build.bat 더블클릭
```

OC 코드 입력 후 `beopsuny-skill.zip`이 생성됩니다.
Claude Desktop의 Skills 메뉴에서 이 zip 파일을 추가하세요.

### 방법 2: Claude Code Skill로 사용

`.claude/skills/beopsuny/` 폴더를 프로젝트에 복사합니다.

```bash
cd .claude/skills/beopsuny/config
cp settings.yaml.example settings.yaml
```

`settings.yaml`에 OC 코드를 설정합니다:

```yaml
oc_code: "your_email_id"  # open.law.go.kr 가입 이메일의 @ 앞부분
```

OC 코드는 [국가법령정보 공동활용](https://open.law.go.kr)에서 회원가입 후 확인할 수 있습니다.

### 3. 의존성

```bash
pip install pyyaml
```

## 사용법

### 법령 검색

```bash
python scripts/fetch_law.py search "민법"
python scripts/fetch_law.py search "개인정보" --sort date
python scripts/fetch_law.py search "횡령" --type prec  # 판례
```

### 법령 다운로드

```bash
python scripts/fetch_law.py fetch --name "민법"
python scripts/fetch_law.py fetch --case "2022다12345"  # 판례
```

### 링크 생성

```bash
python scripts/gen_link.py law "민법" --article 750
python scripts/gen_link.py case "2022다12345"
```

## 검색 대상

| 코드 | 대상 | 설명 |
|------|------|------|
| `law` | 법령 | 법률, 대통령령, 부령 |
| `prec` | 판례 | 대법원, 하급심 판결 |
| `ordin` | 자치법규 | 조례, 규칙 |
| `admrul` | 행정규칙 | 훈령, 예규, 고시 |
| `expc` | 법령해석례 | 법제처 해석 |
| `detc` | 헌재결정례 | 헌법재판소 결정 |

## 핵심 원칙

1. **정확한 인용**: 구체적인 조문/판례 번호 명시
2. **검증 가능한 링크**: law.go.kr 직접 링크 제공
3. **시행일 확인**: 현행 여부와 시행일자 표시
4. **면책 고지**: 정식 법률 자문은 변호사 상담 필요

## 참고 사이트

| 사이트 | URL | 용도 |
|--------|-----|------|
| 국가법령정보센터 | law.go.kr | 법령/판례 원문 |
| 대법원 종합법률정보 | glaw.scourt.go.kr | 판례 원문 |
| 케이스노트 | casenote.kr | AI 판례 검색 |
| 빅케이스 | bigcase.ai | 유사 판례 추천 |

## 라이선스

MIT License
