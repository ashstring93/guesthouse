"""
애플리케이션 전역 설정 모듈.

환경변수 로드, 경로 상수, 요금 상수, 공휴일 세트, 약관 카탈로그 등
프로젝트 전반에서 사용하는 설정값을 한곳에서 관리합니다.

다른 모듈에서 사용 시:
    from config import BACKEND_DIR, BASE_WEEKDAY_RATE, HOLIDAY_DATES
"""

import os
from datetime import date
from pathlib import Path

import holidays
from dotenv import load_dotenv

# ── 경로 상수 ──
# __file__ 기준으로 backend/, project root, frontend 디렉토리를 결정합니다.
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
RESERVATION_PAGES_DIR = FRONTEND_DIR / "pages" / "reservation"

# ── 환경변수 로드 ──
# .env 파일은 backend/ 디렉토리에만 존재합니다.
load_dotenv(BACKEND_DIR / ".env")

# ── 데이터베이스 경로 ──
DB_PATH = BACKEND_DIR / "guesthouse.db"

# ── 숙소 요금 상수 ──
# 기본 요금: 평일/주말 기준 1박 요금
BASE_WEEKDAY_RATE = int(os.getenv("BASE_WEEKDAY_RATE", "184847"))
BASE_WEEKEND_RATE = int(os.getenv("BASE_WEEKEND_RATE", "242612"))

# 인원 관련 상수
BASE_GUESTS = int(os.getenv("BASE_GUESTS", "2"))  # 기본 인원 (추가 요금 없음)
MAX_GUESTS = int(os.getenv("MAX_GUESTS", "6"))  # 최대 수용 인원

# 추가 요금
ADULT_EXTRA_FEE = int(os.getenv("ADULT_EXTRA_FEE", "20000"))  # 추가 인원 1인당 1박 요금
BBQ_FEE = int(os.getenv("BBQ_FEE", "20000"))  # BBQ 옵션 요금

# ── 토스페이먼츠 설정 ──
TOSSPAYMENTS_API_BASE = os.getenv(
    "TOSSPAYMENTS_API_BASE", "https://api.tosspayments.com"
).rstrip("/")
TOSSPAYMENTS_SECRET_KEY = os.getenv("TOSSPAYMENTS_SECRET_KEY", "")

# ── 관리자 대시보드 ──
ADMIN_TOKEN = os.getenv("ADMIN_DASHBOARD_TOKEN", "").strip()

# ── CORS 설정 ──
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8000").split(",")

# ── 공휴일 세트 ──
# holidays 라이브러리로 한국 공휴일을 자동 생성하고,
# 환경변수에 수동으로 추가한 날짜를 병합합니다.
current_year = date.today().year
kr_holidays = holidays.KR(years=[current_year, current_year + 1, current_year + 2])
DYNAMIC_HOLIDAY_DATES = {str(d) for d in kr_holidays.keys()}

ENV_HOLIDAY_DATES = {
    value.strip()
    for value in os.getenv("HOLIDAY_DATES", "").split(",")
    if value.strip()
}
HOLIDAY_DATES = DYNAMIC_HOLIDAY_DATES | ENV_HOLIDAY_DATES

# ── 약관/예약 상태 필터 ──
TERMS_VERSION = os.getenv("PAYMENT_TERMS_VERSION", "2026-02-24-v1").strip()

# 예약 현황 캘린더에서 마감으로 표시할 결제 상태 목록
BOOKED_STATUS_FILTER = tuple(
    status.strip().lower()
    for status in os.getenv("BOOKED_STATUSES", "pending,confirmed,paid").split(",")
    if status.strip()
)

# ── 약관 카탈로그 ──
# 각 약관의 제목과 요약 텍스트를 정의합니다.
# 결제 시 약관 동의 기록(payment_term_consents)에 snapshot으로 저장됩니다.
PAYMENT_TERMS_CATALOG = {
    "policy": {
        "title": "유의사항/환불규정 동의",
        "snapshot_text": (
            "체크인/체크아웃 및 환불 기준: 7일 전 전액 환불, 6~3일 전 50%, 2일 이내 환불 불가."
        ),
    },
    "privacy": {
        "title": "개인정보 수집 및 이용동의",
        "snapshot_text": (
            "수집 항목(예약자명/연락처/결제확인정보), 이용 목적(예약·결제·문의 대응), 법정 보유기간 보관."
        ),
    },
    "thirdparty": {
        "title": "개인정보 제3자 제공동의",
        "snapshot_text": (
            "제공 대상(PG/카드사/간편결제사), 제공 항목(주문번호/결제금액 등), 제공 목적(승인·정산·환불)."
        ),
    },
    "adult": {
        "title": "미성년자 아님 동의",
        "snapshot_text": "예약자는 본인이며 미성년자가 아니고 본인 명의로 예약/결제를 진행합니다.",
    },
}

# ── 챗봇 이미지 매핑 ──
# 챗봇 응답 텍스트에 특정 키워드가 포함되면, 관련 이미지를 응답 끝에 자동 첨부합니다.
# 키: 감지할 키워드 (응답 텍스트에 포함 여부 확인)
# 값: 첨부할 이미지 목록 (alt=설명, path=정적 파일 경로)
CHATBOT_IMAGE_MAP = {
    "주차": [
        {"alt": "집 앞 대로변 주차장", "path": "/images/chatbot/parking-street.png"},
        {"alt": "태평 성결교회 인근 주차장", "path": "/images/chatbot/parking-lot.png"},
    ],
}
