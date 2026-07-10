# 🌙 korean-lunar-calendar-data

> 한국천문연구원 공식 API 기반 음양력 변환 데이터 일괄 다운로더

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-ea4aaa?style=flat-square&logo=github-sponsors)](https://github.com/sponsors/veryfaraway)
[![Ko-fi](https://img.shields.io/badge/Support-Ko--fi-ff5e5b?style=flat-square&logo=kofi&logoColor=white)](https://ko-fi.com/eoneone)

공공데이터포털의 [한국천문연구원 음양력 정보제공 서비스](https://www.data.go.kr/data/15012679/openapi.do) API를 사용하여
**1826년~2050년** (225년간, 약 82,000일) 의 양력↔음력 변환 데이터를 일괄 다운로드합니다.

## ✨ 주요 기능

| 기능 | 설명 |
|------|------|
| 📅 대량 수집 | 지정 기간의 모든 양력일에 대한 음력 변환 데이터 일괄 다운로드 |
| 💾 다중 포맷 | JSON + CSV (Excel 호환 UTF-8 BOM) 동시 출력 |
| ⏸ 중단/재개 | Ctrl+C로 중단해도 진행 상태 저장, 재실행 시 이어서 다운로드 |
| 🔄 자동 재시도 | 네트워크 오류·429·5xx 시 지수 백오프로 최대 5회 재시도 |
| ⠋ 실시간 스피너 | 프로그레스 바 + 경과 시간 + ETA 표시 (터미널 회전 애니메이션) |
| ☁️ GitHub Actions | 클라우드에서 병렬 다운로드 (로컬 PC를 묶어두지 않아도 됨) |

### 실행 화면

```
============================================================
📅 한국천문연구원 음양력 데이터 다운로드
   기간: 1826년 ~ 2050년
   총 일수: 82,127일
   예상 소요 시간: ~68분
   출력: data/lunar_solar_1826_2050.json
         data/lunar_solar_1826_2050.csv
============================================================

  ⠹ 1842-07-23 |███░░░░░░░░░░░░░░░░░| 6,043/82,127 (7.4%) | ✅6,043 ❌0 | ⏱5분02초 남은:62분18초
```

---

## 📦 수집 데이터 스키마

각 날짜별로 아래 14개 항목이 수집됩니다:

| 필드 | 한글명 | 예시 | 설명 |
|------|--------|------|------|
| `solYear` | 양력년 | `2025` | |
| `solMonth` | 양력월 | `01` | |
| `solDay` | 양력일 | `29` | |
| `solWeek` | 요일 | `수` | |
| `solLeapyear` | 윤년여부 | `평` | 평: 평년, 윤: 윤년 |
| `solJd` | 율리우스적일 | `2460705` | Julian Day Number |
| `lunYear` | 음력년 | `2025` | |
| `lunMonth` | 음력월 | `01` | |
| `lunDay` | 음력일 | `01` | |
| `lunLeapmonth` | 윤달여부 | `평` | 평: 평달, 윤: 윤달 |
| `lunNday` | 음력월일수 | `29` | 해당 음력 월의 총 일수 |
| `lunSecha` | 세차 | `을사(乙巳)` | 연간지 (60갑자) |
| `lunWolgeon` | 월건 | `무인(戊寅)` | 월간지 |
| `lunIljin` | 일진 | `병인(丙寅)` | 일간지 |

---

## 🚀 빠른 시작

### 사전 준비

1. [공공데이터포털](https://data.go.kr)에서 **한국천문연구원 음양력 정보제공 서비스** 활용 신청
2. 발급받은 서비스키(인코딩)를 `.env` 파일에 설정:

```bash
# .env
SERVICE_KEY=발급받은_서비스키
```

### 로컬 실행

```bash
# 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 설치
pip install requests

# 기본 실행 (1826~2050년 전체, 약 68분)
python download_lunar_solar.py

# 특정 기간만 다운로드
python download_lunar_solar.py --start 2000 --end 2025

# 처음부터 다시 시작 (기존 진행 상태 무시)
python download_lunar_solar.py --no-resume

# 출력 디렉토리 지정
python download_lunar_solar.py --output ./my_data
```

### 예상 소요 시간 (로컬)

| 기간 | 일수 | 소요 시간 |
|------|------|----------|
| 1826~2050 (225년) | ~82,000일 | ~68분 |
| 2000~2050 (51년) | ~18,600일 | ~16분 |
| 2020~2030 (11년) | ~4,000일 | ~3분 |

---

## ☁️ GitHub Actions로 실행 (권장)

로컬 PC를 오래 묶어두기 싫다면 **GitHub Actions**에서 실행할 수 있습니다.
일일 API 호출 한도를 자동 인식하여 **병렬/단일 전략을 지능적으로 선택**합니다.

### 설정

1. **Secrets 등록**: 리포지토리 `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

   | Name | Value | 필수 |
   |------|-------|------|
   | `SERVICE_KEY` | 공공데이터포털에서 발급받은 서비스키 | ✅ |
   | `TELEGRAM_BOT_TOKEN` | 텔레그램 봇 토큰 ([BotFather](https://t.me/BotFather)에서 발급) | 선택 |
   | `TELEGRAM_CHAT_ID` | 알림 받을 채팅 ID ([userinfobot](https://t.me/userinfobot)으로 확인) | 선택 |

2. **워크플로우 실행**: `Actions` 탭 → `음양력 데이터 다운로드` → `Run workflow`

   | 입력 | 기본값 | 설명 |
   |------|--------|------|
   | `start_year` | `1826` | 시작 연도 |
   | `end_year` | `2050` | 종료 연도 |
   | `daily_limit` | `10000` | 일일 API 호출 한도 (0=무제한) |

3. **결과 다운로드**: 워크플로우 완료 후 하단 `Artifacts` 섹션에서 ZIP 다운로드 (90일 보관)

### 지능형 실행 모드

워크플로우는 **총 일수 vs 일일 한도**를 비교하여 자동으로 최적 전략을 선택합니다:

| 조건 | 모드 | 동작 |
|------|------|------|
| 총 일수 ≤ 일일 한도 | 🚀 **병렬** | 5분할 동시 다운로드 → 자동 병합 |
| 총 일수 > 일일 한도 | 📊 **단일 이어받기** | 한도까지 수집 → 저장 → 다음 실행 시 이어서 |

> 💡 1826~2050년(82,000일)을 일일 한도 10,000건으로 받으면, **약 9일**에 걸쳐 자동 완료됩니다.

### 📱 텔레그램 알림

텔레그램 Secrets를 등록해두면 매 실행마다 자동으로 알림을 보내줍니다:

- **매일 실행 후**: 오늘 수집 건수, 누적 진행률(%), 남은 예상 일수
- **전체 완료 시**: 🎉 완료 알림 + cron 스케줄 비활성화 안내

> 텔레그램 Secrets 미등록 시 알림 없이 정상 동작합니다.

### ⏰ 대량 다운로드 자동화 (cron)

매일 수동으로 "Run workflow"를 누르기 싫다면, `.github/workflows/download.yml`의 `schedule` 주석을 해제하세요:

```yaml
schedule:
  - cron: '0 15 * * *'  # 매일 KST 00:00 (UTC 15:00)
```

활성화하면 매일 자정에 자동 실행 → 한도까지 수집 → 텔레그램 알림 → 며칠 후 완료 시 비활성화 안내까지 받을 수 있습니다.

> 💡 **무료 플랜 (2,000분/월)** 으로 충분히 실행 가능합니다.

---

## 📁 출력 파일

```text
data/
├── lunar_solar_1826_2050.json    # JSON 배열 (전체 데이터)
├── lunar_solar_1826_2050.csv     # CSV (Excel 호환 UTF-8 BOM)
└── failed_1826_2050.json         # 실패한 날짜 목록 (있을 경우만)
```

### JSON 예시

```json
[
  {
    "solYear": "2025",
    "solMonth": "01",
    "solDay": "29",
    "solWeek": "수",
    "solLeapyear": "평",
    "solJd": "2460705",
    "lunYear": "2025",
    "lunMonth": "01",
    "lunDay": "01",
    "lunLeapmonth": "평",
    "lunNday": "29",
    "lunSecha": "을사(乙巳)",
    "lunWolgeon": "무인(戊寅)",
    "lunIljin": "병인(丙寅)"
  }
]
```

---

## 🗂 프로젝트 구조

```text
.
├── download_lunar_solar.py          # 메인 다운로드 스크립트
├── .env                             # 서비스키 설정 (git에서 제외)
├── .github/
│   └── workflows/
│       └── download.yml             # GitHub Actions 워크플로우
├── data/                            # 출력 디렉토리 (git에서 제외)
├── docs/                            # API 가이드 문서 (PDF)
└── README.md
```

---

## ❓ FAQ

**Q: API 데이터 제공 범위가 1826~2050년인가요?**
> 한국천문연구원 음양력 정보제공 서비스의 데이터는 양력 기준 1391년~2050년까지 제공됩니다.
> 이 프로그램의 기본값(1826~2050)은 근현대 실용 범위를 고려한 것이며, `--start` 옵션으로 더 이전 연도도 가능합니다.

**Q: 중간에 끊겼는데 어떻게 하나요?**
> 다시 같은 명령어로 실행하면 자동으로 마지막 성공 지점부터 이어서 다운로드합니다.
> 처음부터 다시 받으려면 `--no-resume` 옵션을 사용하세요.

**Q: GitHub Actions 병렬 모드에서 429 에러가 나면?**
> 공공데이터포털 API는 IP 기반 30 tps 제한이 있습니다. GitHub Actions 러너는 보통 서로 다른 IP를 사용하므로 문제없지만,
> 만약 429가 빈번하면 단일 모드(`parallel: false`)를 사용하세요.

**Q: 이 데이터로 무엇을 할 수 있나요?**

> - 음력 생일/기념일 → 양력 날짜 변환
> - 전통 명절(설날, 추석 등) 날짜 조회
> - 60갑자 일진/세차 기반 분석
> - 오프라인 음양력 달력 앱 제작

---

## 📡 API 출처

- **서비스**: [한국천문연구원 천문우주정보 - 음양력 정보제공 서비스](https://www.data.go.kr/data/15012679/openapi.do)
- **오퍼레이션**: `getLunCalInfo` (양력 → 음력 변환)
- **Base URL**: `http://apis.data.go.kr/B090041/openapi/service/LrsrCldInfoService`
- **제공 기관**: 한국천문연구원 (KASI)

---

## 💖 후원 (Support)

이 프로젝트가 도움이 되셨다면 후원을 통해 개발자를 응원해주세요!

<a href="https://github.com/sponsors/veryfaraway">
  <img src="https://img.shields.io/badge/Sponsor-GitHub_Sponsors-ea4aaa?style=for-the-badge&logo=github-sponsors&logoColor=white" alt="GitHub Sponsors" />
</a>
<a href="https://ko-fi.com/eoneone">
  <img src="https://storage.ko-fi.com/cdn/brandasset/kofi_button_blue.png" alt="Buy Me a Coffee at ko-fi.com" height="36" />
</a>

---

## 📄 라이선스

이 프로그램의 소스 코드는 MIT License로 배포됩니다.

수집된 데이터의 저작권은 [한국천문연구원](https://kasi.re.kr)에 있으며,
[공공데이터포털 이용약관](https://data.go.kr)에 따라 활용하시기 바랍니다.
