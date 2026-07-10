# Changelog

이 프로젝트의 주요 변경 사항을 기록합니다.
형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/)를 따릅니다.

## [Unreleased]

### Added
- **일일 API 호출 한도 (`--daily-limit`)**: 공공데이터포털 일일 트래픽 제한에 맞춰 한도 도달 시 진행 저장 후 안전하게 종료, 재실행 시 자동 이어받기
- **연속 실패 조기 중단**: 20건 연속 실패 시 즉시 중단하여 서비스키 오류/API 장애 상황에서 불필요한 대기 방지
- **500건 단위 중간 저장**: 연도 전환 시에만 저장하던 방식에서 500건마다 자동 저장으로 변경, 취소/장애 시 데이터 소실 최소화
- **지능형 워크플로우 전략**: 총 건수 ≤ 일일 한도면 병렬 5분할, 초과 시 단일 이어받기 모드 자동 선택
- **텔레그램 알림 연동**: 매일 실행 결과(누적 진행률, 남은 일수), 전체 완료 시 cron 비활성화 안내 자동 발송
- **GitHub Actions cron 스케줄**: 매일 자동 실행으로 대량 데이터 며칠에 걸쳐 무인 완료 지원
- **`if: always()` artifact 보호**: 워크플로우 취소/실패 시에도 수집 데이터 artifact 업로드 보장

### Changed
- **워크플로우 입력 변경**: `parallel` (true/false) → `daily_limit` (건수)로 더 직관적인 제어
- **README 전면 개편**: 지능형 실행 모드, 텔레그램 알림, cron 자동화, Secrets 설정 가이드 추가

## [0.2.0] - 2026-07-09

### Added
- **Braille 스피너 애니메이션**: 실시간 진행 표시 (날짜, 프로그레스 바, 경과/남은 시간, 성공/실패 건수)
- **CI 환경 자동 감지**: 비TTY 환경에서 30초 간격 텍스트 출력으로 자동 전환
- **GitHub Actions 워크플로우**: 병렬 matrix 다운로드 + 자동 병합 지원
- **GitHub Sponsors / Ko-fi 후원 버튼**: README 상단 배지 + 하단 후원 섹션

### Changed
- **README 업데이트**: 프로젝트 소개, 데이터 스키마, 로컬/CI 사용법, FAQ 등 전면 작성

## [0.1.0] - 2026-07-09

### Added
- **초기 다운로드 스크립트** (`download_lunar_solar.py`): 공공데이터포털 `getLunCalInfo` API 호출
- **JSON + CSV 동시 출력**: UTF-8 BOM CSV (Excel 호환)
- **재개(Resume) 기능**: Ctrl+C 중단 후 이어받기
- **지수 백오프 재시도**: HTTP 429/5xx 시 최대 5회 자동 재시도
- **`.env` 기반 서비스키 관리**
- **`.gitignore`**: `.venv`, `data/`, `.env` 제외
