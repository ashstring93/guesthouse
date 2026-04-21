"""환경변수와 전역 설정."""

import os
from datetime import date
from pathlib import Path

import holidays
from dotenv import load_dotenv


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _env_csv(name: str, default: str) -> tuple[str, ...]:
    return tuple(
        value.strip()
        for value in os.getenv(name, default).split(",")
        if value.strip()
    )


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
RESERVATION_PAGES_DIR = FRONTEND_DIR / "pages" / "reservation"

load_dotenv(BACKEND_DIR / ".env")

DB_PATH = Path(os.getenv("DB_PATH", str(BACKEND_DIR / "guesthouse.db"))).expanduser()

BASE_WEEKDAY_RATE = _env_int("BASE_WEEKDAY_RATE", 184847)
BASE_WEEKEND_RATE = _env_int("BASE_WEEKEND_RATE", 242612)
BASE_GUESTS = _env_int("BASE_GUESTS", 2)
MAX_GUESTS = _env_int("MAX_GUESTS", 8)
ADULT_EXTRA_FEE = _env_int("ADULT_EXTRA_FEE", 20000)
BBQ_FEE = _env_int("BBQ_FEE", 20000)

TOSSPAYMENTS_API_BASE = os.getenv(
    "TOSSPAYMENTS_API_BASE", "https://api.tosspayments.com"
).rstrip("/")
TOSSPAYMENTS_WIDGET_CLIENT_KEY = os.getenv("TOSSPAYMENTS_WIDGET_CLIENT_KEY", "")
TOSSPAYMENTS_PAYMENT_METHOD_VARIANT_KEY = os.getenv(
    "TOSSPAYMENTS_PAYMENT_METHOD_VARIANT_KEY", "DEFAULT"
).strip()
TOSSPAYMENTS_SECRET_KEY = os.getenv("TOSSPAYMENTS_SECRET_KEY", "")

ADMIN_TOKEN = os.getenv("ADMIN_DASHBOARD_TOKEN", "").strip()
CORS_ORIGINS = list(_env_csv("CORS_ORIGINS", "http://localhost:8000"))

CURRENT_YEAR = date.today().year
KR_HOLIDAYS = holidays.KR(years=[CURRENT_YEAR, CURRENT_YEAR + 1, CURRENT_YEAR + 2])
HOLIDAY_DATES = {str(d) for d in KR_HOLIDAYS.keys()} | set(
    _env_csv("HOLIDAY_DATES", "")
)

TERMS_VERSION = os.getenv("PAYMENT_TERMS_VERSION", "2026-03-09-v1").strip()
BOOKED_STATUS_FILTER = tuple(
    status.lower() for status in _env_csv("BOOKED_STATUSES", "confirming,confirmed,paid")
)

PAYMENT_TERMS_CATALOG = {
    "policy": {
        "title": "숙소 이용 및 환불규정 동의",
        "snapshot_text": (
            "체크인은 오후 3시 이후, 체크아웃은 오전 11시까지이며, 체크인 7일 전까지 취소 시 100% 환불, "
            "6일~3일 전 취소 시 50% 환불, 2일 이내 취소는 환불이 어렵습니다."
        ),
    },
    "privacy": {
        "title": "개인정보 수집 및 이용동의",
        "snapshot_text": (
            "수집 항목은 예약자명, 연락처, 체크인 일정, 결제 관련 확인 정보이며, 예약 확인, 숙박 서비스 제공, "
            "결제 처리, 문의 응대, 관계 법령상 거래기록 보존 목적으로 이용합니다."
        ),
    },
    "thirdparty": {
        "title": "결제 처리 관련 개인정보 제공 동의",
        "snapshot_text": (
            "제공 대상은 토스페이먼츠, 카드사, 은행, 간편결제 사업자 등 결제수단 관련 사업자이며, "
            "제공 항목은 예약자명, 연락처, 주문번호, 결제금액 등 결제 승인과 환불 처리에 필요한 정보입니다."
        ),
    },
    "adult": {
        "title": "성인 본인 예약 확인",
        "snapshot_text": (
            "예약자는 만 19세 이상 성인이며 본인 명의로 예약과 결제를 진행하고, 미성년자의 무단 예약이 확인되는 경우 "
            "추가 확인 또는 예약 취소가 이뤄질 수 있음을 확인합니다."
        ),
    },
}

CHATBOT_IMAGE_MAP = {
    "주차": [
        {"alt": "집 앞 대로변 주차장", "path": "/images/chatbot/parking-street.png"},
        {"alt": "태평 성결교회 인근 주차장", "path": "/images/chatbot/parking-lot.png"},
    ],
}
