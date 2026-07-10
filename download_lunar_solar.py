#!/usr/bin/env python3
"""
한국천문연구원 음양력 정보 다운로더

공공데이터포털 API(LrsrCldInfoService)를 사용하여
지정된 기간의 양력↔음력 변환 데이터를 일괄 다운로드합니다.

API: getLunCalInfo (양력 → 음력 변환)
출처: 한국천문연구원 천문우주정보 - 음양력 정보제공 서비스

사용법:
  1. .env 파일에 SERVICE_KEY=<발급받은 서비스키> 설정
  2. python download_lunar_solar.py

출력: data/lunar_solar_YYYY_YYYY.json, data/lunar_solar_YYYY_YYYY.csv
"""

import csv
import json
import os
import sys
import time
import calendar
import argparse
import signal
import threading
from datetime import date, timedelta
from pathlib import Path
from xml.etree import ElementTree

import requests


# ─────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────
BASE_URL = (
    "http://apis.data.go.kr/B090041/openapi/service/LrsrCldInfoService/getLunCalInfo"
)

# 응답 XML 필드 → 사람이 읽을 수 있는 한글 헤더
FIELDS = [
    ("solYear", "양력년"),
    ("solMonth", "양력월"),
    ("solDay", "양력일"),
    ("solWeek", "요일"),
    ("solLeapyear", "윤년여부"),
    ("solJd", "율리우스적일"),
    ("lunYear", "음력년"),
    ("lunMonth", "음력월"),
    ("lunDay", "음력일"),
    ("lunLeapmonth", "윤달여부"),
    ("lunNday", "음력월일수"),
    ("lunSecha", "세차"),
    ("lunWolgeon", "월건"),
    ("lunIljin", "일진"),
]

FIELD_KEYS = [f[0] for f in FIELDS]

# API 호출 제한: 30 tps → 안전하게 초당 20건
CALLS_PER_SECOND = 20
DELAY = 1.0 / CALLS_PER_SECOND

# 재시도 설정
MAX_RETRIES = 5
RETRY_BACKOFF = 2.0  # 지수 백오프 기본 초

# 연속 실패 시 조기 중단 임계값
CONSECUTIVE_FAIL_LIMIT = 20

# 기본 일일 API 호출 한도 (공공데이터포털 기본값)
DEFAULT_DAILY_LIMIT = 0  # 0 = 무제한

# 스피너 문자 (Braille 패턴)
SPINNER_CHARS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


class Spinner:
    """
    백그라운드 스레드에서 터미널에 회전 애니메이션을 표시합니다.
    진행률, 경과 시간, ETA 등을 함께 보여줍니다.

    TTY가 아닌 환경(CI 등)에서는 주기적 줄 출력으로 fallback합니다.
    """

    def __init__(self):
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._is_tty = sys.stderr.isatty()
        # 외부에서 업데이트하는 상태
        self.current_date = ""
        self.done = 0
        self.total = 0
        self.count = 0
        self.failed = 0
        self.start_time = time.time()

    def start(self):
        self._stop_event.clear()
        self.start_time = time.time()
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self, final_msg: str = ""):
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        if self._is_tty:
            # 스피너 줄 지우기
            sys.stderr.write("\r" + " " * 120 + "\r")
            sys.stderr.flush()
        if final_msg:
            print(final_msg)

    def update(self, current_date: str, done: int, count: int, failed: int):
        with self._lock:
            self.current_date = current_date
            self.done = done
            self.count = count
            self.failed = failed

    def _format_time(self, seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.0f}초"
        elif seconds < 3600:
            m, s = divmod(int(seconds), 60)
            return f"{m}분{s:02d}초"
        else:
            h, rem = divmod(int(seconds), 3600)
            m, s = divmod(rem, 60)
            return f"{h}시간{m:02d}분"

    def _build_line(self, char: str) -> str:
        """진행 상태 문자열을 생성합니다."""
        with self._lock:
            d = self.current_date
            done = self.done
            total = self.total
            count = self.count
            failed = self.failed

        elapsed = time.time() - self.start_time

        if total > 0 and done > 0:
            pct = done / total * 100
            bar_len = 20
            filled = int(bar_len * done / total)
            bar = "█" * filled + "░" * (bar_len - filled)
            rate = done / elapsed if elapsed > 0 else 0
            remaining = (total - done) / rate if rate > 0 else 0
            eta_str = self._format_time(remaining)
            elapsed_str = self._format_time(elapsed)

            return (
                f"  {char} {d} |{bar}| "
                f"{done:,}/{total:,} ({pct:.1f}%) | "
                f"✅{count:,} ❌{failed} | "
                f"⏱{elapsed_str} 남은:{eta_str}"
            )
        return f"  {char} 준비 중..."

    def _spin(self):
        idx = 0
        last_ci_log = 0  # CI 모드에서 마지막 줄 출력 시각
        while not self._stop_event.is_set():
            char = SPINNER_CHARS[idx % len(SPINNER_CHARS)]
            line = self._build_line(char)

            if self._is_tty:
                # TTY: 같은 줄에서 회전 애니메이션
                try:
                    cols = os.get_terminal_size().columns
                except OSError:
                    cols = 80
                line = line[:cols - 1]
                sys.stderr.write("\r" + line + " " * max(0, cols - len(line) - 1))
                sys.stderr.flush()
                self._stop_event.wait(0.08)  # ~12fps
            else:
                # Non-TTY (CI): 30초마다 한 줄 출력
                now = time.time()
                if now - last_ci_log >= 30:
                    print(line, flush=True)
                    last_ci_log = now
                self._stop_event.wait(1.0)

            idx += 1


# ─────────────────────────────────────────────
# 유틸리티
# ─────────────────────────────────────────────
def load_service_key() -> str:
    """
    서비스키를 환경변수 또는 .env 파일에서 로드합니다.
    """
    key = os.environ.get("SERVICE_KEY")
    if key:
        return key

    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == "SERVICE_KEY":
                return v.strip()

    print("❌ SERVICE_KEY를 찾을 수 없습니다.")
    print("   방법 1: .env 파일에 SERVICE_KEY=<서비스키> 추가")
    print("   방법 2: 환경변수 SERVICE_KEY 설정")
    sys.exit(1)


def date_range(start: date, end: date):
    """start부터 end까지 하루씩 순회하는 제너레이터."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def total_days(start: date, end: date) -> int:
    """기간 내 총 일수."""
    return (end - start).days + 1


def parse_item(xml_text: str) -> dict | None:
    """
    API 응답 XML에서 item 데이터를 파싱합니다.
    오류 시 None 반환.
    """
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return None

    # 에러 응답 확인
    result_code_elem = root.find(".//resultCode")
    if result_code_elem is not None and result_code_elem.text != "00":
        result_msg = root.find(".//resultMsg")
        msg = result_msg.text if result_msg is not None else "UNKNOWN"
        print(f"  ⚠ API 에러: {result_code_elem.text} - {msg}")
        return None

    item = root.find(".//item")
    if item is None:
        return None

    record = {}
    for key in FIELD_KEYS:
        elem = item.find(key)
        record[key] = elem.text if elem is not None else ""
    return record


def fetch_day(session: requests.Session, service_key: str, d: date) -> dict | None:
    """
    특정 양력일의 음양력 데이터를 API에서 가져옵니다.
    재시도 로직 포함.
    """
    params = {
        "solYear": f"{d.year:04d}",
        "solMonth": f"{d.month:02d}",
        "solDay": f"{d.day:02d}",
        "ServiceKey": service_key,
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(BASE_URL, params=params, timeout=10)
            if resp.status_code == 200:
                record = parse_item(resp.text)
                if record is not None:
                    return record
            # 429 또는 5xx → 재시도
            if resp.status_code in (429, 500, 502, 503, 504):
                wait = RETRY_BACKOFF * (2 ** attempt)
                print(f"  ⏳ HTTP {resp.status_code}, {wait:.1f}초 후 재시도...")
                time.sleep(wait)
                continue
            # 기타 에러
            print(f"  ⚠ HTTP {resp.status_code} for {d}")
            return None

        except requests.exceptions.RequestException as e:
            wait = RETRY_BACKOFF * (2 ** attempt)
            print(f"  ⚠ 연결 오류: {e}, {wait:.1f}초 후 재시도...")
            time.sleep(wait)

    print(f"  ❌ {MAX_RETRIES}번 재시도 실패: {d}")
    return None


# ─────────────────────────────────────────────
# 진행 상태 저장/복원 (재개 기능)
# ─────────────────────────────────────────────
def get_progress_path(start_year: int, end_year: int) -> Path:
    return Path(__file__).parent / "data" / f".progress_{start_year}_{end_year}.json"


def save_progress(progress_path: Path, last_date: date, count: int):
    """진행 상태를 파일에 저장."""
    progress_path.write_text(
        json.dumps(
            {"last_date": last_date.isoformat(), "count": count},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def load_progress(progress_path: Path) -> tuple[date | None, int]:
    """저장된 진행 상태를 로드. 없으면 (None, 0) 반환."""
    if not progress_path.exists():
        return None, 0
    try:
        data = json.loads(progress_path.read_text(encoding="utf-8"))
        return date.fromisoformat(data["last_date"]), data["count"]
    except (json.JSONDecodeError, KeyError):
        return None, 0


# ─────────────────────────────────────────────
# 메인 다운로드 로직
# ─────────────────────────────────────────────
def download_range(
    start_year: int,
    end_year: int,
    service_key: str,
    output_dir: Path,
    resume: bool = True,
    daily_limit: int = 0,
):
    """
    start_year~end_year 기간의 모든 양력일에 대해
    음양력 데이터를 다운로드합니다.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    start_date = date(start_year, 1, 1)
    end_date = date(end_year, 12, 31)

    json_path = output_dir / f"lunar_solar_{start_year}_{end_year}.json"
    csv_path = output_dir / f"lunar_solar_{start_year}_{end_year}.csv"
    progress_path = get_progress_path(start_year, end_year)

    # 재개 지점 확인
    resume_date = None
    existing_count = 0
    if resume:
        resume_date, existing_count = load_progress(progress_path)

    if resume_date and resume_date >= start_date:
        actual_start = resume_date + timedelta(days=1)
        if actual_start > end_date:
            print(f"✅ 이미 완료됨! ({existing_count}건)")
            return
        print(f"📂 이전 진행 상태 발견: {resume_date}까지 {existing_count}건 완료")
        print(f"   {actual_start}부터 이어서 다운로드합니다.")
        mode = "a"  # 기존 파일에 추가
    else:
        actual_start = start_date
        existing_count = 0
        mode = "w"

    total = total_days(start_date, end_date)
    remaining = total_days(actual_start, end_date)

    # 이번 실행에서 처리할 건수 결정
    effective_remaining = remaining
    if daily_limit > 0:
        effective_remaining = min(remaining, daily_limit)

    print(f"\n{'='*60}")
    print(f"📅 한국천문연구원 음양력 데이터 다운로드")
    print(f"   기간: {start_year}년 ~ {end_year}년")
    print(f"   총 일수: {total:,}일")
    if mode == "a":
        print(f"   남은 일수: {remaining:,}일 (이미 {existing_count:,}건 완료)")
    if daily_limit > 0:
        print(f"   일일 한도: {daily_limit:,}건 (이번 실행: 최대 {effective_remaining:,}건)")
    print(f"   예상 소요 시간: ~{effective_remaining / CALLS_PER_SECOND / 60:.0f}분")
    print(f"   출력: {json_path}")
    print(f"         {csv_path}")
    print(f"{'='*60}\n")

    # 데이터 수집
    records: list[dict] = []
    if mode == "a" and json_path.exists():
        # 기존 데이터 로드
        existing_data = json.loads(json_path.read_text(encoding="utf-8"))
        records = existing_data
        print(f"   기존 데이터 {len(records)}건 로드 완료\n")

    session = requests.Session()
    session.headers.update({"Accept": "application/xml"})

    count = existing_count
    api_calls = 0  # 이번 실행에서의 API 호출 수
    failed = []
    consecutive_fails = 0
    quota_reached = False

    # Ctrl+C 시 진행 상태 저장
    interrupted = False

    def signal_handler(sig, frame):
        nonlocal interrupted
        interrupted = True
        print("\n\n⚠ 중단 감지! 진행 상태를 저장합니다...")

    original_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, signal_handler)

    spinner = Spinner()
    spinner.total = total
    spinner.done = (actual_start - start_date).days
    spinner.count = count
    spinner.start()

    try:
        for d in date_range(actual_start, end_date):
            if interrupted:
                break

            # 일일 한도 체크
            if daily_limit > 0 and api_calls >= daily_limit:
                quota_reached = True
                print(f"\n\n📊 일일 한도 도달 ({daily_limit:,}건). 진행 상태를 저장하고 종료합니다.")
                break

            record = fetch_day(session, service_key, d)
            api_calls += 1

            if record:
                records.append(record)
                count += 1
                consecutive_fails = 0  # 성공 시 리셋
            else:
                failed.append(d.isoformat())
                consecutive_fails += 1

                # 연속 실패 시 조기 중단
                if consecutive_fails >= CONSECUTIVE_FAIL_LIMIT:
                    print(
                        f"\n\n❌ {CONSECUTIVE_FAIL_LIMIT}건 연속 실패. "
                        f"서비스키 또는 API 상태를 확인하세요."
                    )
                    break

            # 스피너 상태 업데이트
            done_from_start = (d - start_date).days + 1
            spinner.update(d.isoformat(), done_from_start, count, len(failed))

            # 중간 저장 (연도 전환 또는 500건마다)
            next_d = d + timedelta(days=1)
            should_save = (
                next_d.year != d.year
                or interrupted
                or api_calls % 500 == 0
            )
            if should_save:
                save_progress(progress_path, d, count)
                json_path.write_text(
                    json.dumps(records, ensure_ascii=False, indent=None),
                    encoding="utf-8",
                )

            time.sleep(DELAY)

    finally:
        spinner.stop()
        signal.signal(signal.SIGINT, original_handler)

    # ─────────────────────────────────────────
    # 결과 저장
    # ─────────────────────────────────────────
    print(f"\n💾 결과 저장 중...")

    # JSON 저장
    json_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"   ✅ JSON: {json_path} ({len(records):,}건)")

    # CSV 저장
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELD_KEYS)
        writer.writeheader()
        writer.writerows(records)
    print(f"   ✅ CSV:  {csv_path} ({len(records):,}건)")

    # 실패 목록
    if failed:
        failed_path = output_dir / f"failed_{start_year}_{end_year}.json"
        failed_path.write_text(
            json.dumps(failed, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"   ⚠ 실패: {failed_path} ({len(failed)}건)")

    # 완료/중단 상태 메시지
    all_done = not interrupted and not failed and not quota_reached and consecutive_fails < CONSECUTIVE_FAIL_LIMIT
    if all_done:
        if progress_path.exists():
            progress_path.unlink()
        print(f"\n🎉 완료! 총 {len(records):,}건 다운로드")
    elif quota_reached:
        save_progress(progress_path, d, count)
        print(
            f"\n📊 일일 한도 정지. 이번 실행: {api_calls:,}건 호출, {count - existing_count:,}건 수집."
            f"\n   다시 실행하면 이어서 다운로드합니다."
        )
    elif interrupted:
        print(f"\n⏸ 중단됨. 다시 실행하면 이어서 다운로드합니다.")
    elif consecutive_fails >= CONSECUTIVE_FAIL_LIMIT:
        save_progress(progress_path, d, count)
        print(f"\n❌ 연속 실패로 중단. 서비스키/API 상태 확인 후 다시 실행하세요.")
    else:
        print(f"\n⚠ 완료 (실패 {len(failed)}건). 실패 목록을 확인하세요.")

    return records


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="한국천문연구원 음양력 데이터 다운로더",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python download_lunar_solar.py                          # 기본: 1826~2050
  python download_lunar_solar.py --start 2000 --end 2025  # 특정 기간
  python download_lunar_solar.py --daily-limit 1000       # 일일 1,000건 제한
  python download_lunar_solar.py --no-resume              # 처음부터 다시
        """,
    )
    parser.add_argument(
        "--start",
        type=int,
        default=1826,
        help="시작 연도 (기본: 1826)",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=2050,
        help="종료 연도 (기본: 2050)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="출력 디렉토리 (기본: ./data)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="이전 진행 상태를 무시하고 처음부터 다시 시작",
    )
    parser.add_argument(
        "--daily-limit",
        type=int,
        default=DEFAULT_DAILY_LIMIT,
        help="일일 API 호출 한도 (기본: 0=무제한). 한도 도달 시 진행 저장 후 종료",
    )

    args = parser.parse_args()

    if args.start > args.end:
        print(f"❌ 시작 연도({args.start})가 종료 연도({args.end})보다 큽니다.")
        sys.exit(1)

    service_key = load_service_key()
    output_dir = Path(args.output) if args.output else Path(__file__).parent / "data"

    download_range(
        start_year=args.start,
        end_year=args.end,
        service_key=service_key,
        output_dir=output_dir,
        resume=not args.no_resume,
        daily_limit=args.daily_limit,
    )


if __name__ == "__main__":
    main()
