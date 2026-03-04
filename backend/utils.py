"""
유틸리티 함수 모듈.

날짜 파싱, 전화번호 정규화, 요금 계산, 환불 금액 산출, 토스페이먼츠 인증 등
여러 라우터에서 공통으로 사용하는 순수 함수들을 제공합니다.

사용 예시:
    from utils import parse_date_or_400, calculate_room_amount, normalize_phone
"""

import base64
import uuid
from datetime import date, datetime, timedelta

from fastapi import HTTPException

from config import (
    ADULT_EXTRA_FEE,
    BASE_GUESTS,
    BASE_WEEKDAY_RATE,
    BASE_WEEKEND_RATE,
    HOLIDAY_DATES,
    TOSSPAYMENTS_SECRET_KEY,
)


# ── 주문번호 생성 ──


def create_order_id() -> str:
    """고유 주문번호를 생성합니다.

    형식: MBA-{YYYYMMDDHHMMSS}-{6자리 UUID}
    예시: MBA-20260304150030-A1B2C3
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"MBA-{timestamp}-{uuid.uuid4().hex[:6].upper()}"


# ── 날짜 파싱 ──


def parse_date_or_400(date_str: str, field_name: str = "checkin_date") -> date:
    """YYYY-MM-DD 문자열을 date 객체로 변환합니다.

    변환 실패 시 400 에러를 발생시킵니다.
    field_name 파라미터로 에러 메시지에 표시할 필드명을 지정할 수 있습니다.
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} 형식이 올바르지 않습니다. (YYYY-MM-DD)",
        ) from exc


# ── 전화번호 정규화 ──


def normalize_phone(value: str) -> str:
    """전화번호에서 숫자만 추출합니다.

    하이픈, 공백 등 특수문자를 제거하고 숫자만 남깁니다.
    예: '010-1234-5678' → '01012345678'
    """
    return "".join(ch for ch in str(value or "") if ch.isdigit())


# ── 객실 요금 계산 ──


def calculate_room_amount(checkin_date: date, nights: int) -> int:
    """체크인 날짜부터 숙박 일수만큼의 객실 요금을 합산합니다.

    금요일/토요일 체크인은 주말 요금(BASE_WEEKEND_RATE),
    그 외는 평일 요금(BASE_WEEKDAY_RATE)이 적용됩니다.
    공휴일 여부는 요금에 직접 영향을 주지 않으나,
    프론트엔드 캘린더에 표시 용도로 사용됩니다.
    """

    def is_premium_rate_day(d: date) -> bool:
        """주말(금/토) 체크인인지 확인합니다."""
        return d.weekday() in (4, 5)

    total = 0
    for offset in range(nights):
        d = checkin_date + timedelta(days=offset)
        total += BASE_WEEKEND_RATE if is_premium_rate_day(d) else BASE_WEEKDAY_RATE
    return total


# ── 추가 인원 요금 계산 ──


def calculate_extra_guest_details(adults: int, nights: int) -> dict:
    """기본 인원 초과 시 추가 인원 요금을 계산합니다.

    기본 인원(BASE_GUESTS, 2명) 초과분에 대해
    1인당 1박 ADULT_EXTRA_FEE(20,000원)를 적용합니다.

    반환값:
        {"extra_guests": 초과 인원수, "extra_amount": 추가 요금 합계}
    """
    extra_guests = max(0, adults - BASE_GUESTS)
    extra_amount = extra_guests * ADULT_EXTRA_FEE * max(1, nights)

    return {
        "extra_guests": extra_guests,
        "extra_amount": extra_amount,
    }


# ── 환불 금액 계산 ──


def calculate_refund_amount(checkin_date_str: str, total_amount: int) -> dict:
    """체크인 날짜 기준 환불 금액을 자동 계산합니다.

    환불 정책:
    - 체크인 7일 이상 전: 전액 환불 (100%)
    - 체크인 3~6일 전: 50% 환불
    - 체크인 2일 이내 (당일 포함): 환불 불가 (0%)

    반환값:
        {"refund_rate": 환불비율, "refund_amount": 환불금액,
         "days_until_checkin": 잔여일, "message": 안내 메시지}
    """
    today = date.today()
    try:
        checkin = datetime.strptime(checkin_date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return {
            "refund_rate": 0,
            "refund_amount": 0,
            "days_until_checkin": -1,
            "message": "체크인 날짜를 파싱할 수 없습니다.",
        }

    days_left = (checkin - today).days

    if days_left >= 7:
        rate = 100
        message = f"체크인 {days_left}일 전 → 전액 환불 (100%)"
    elif 3 <= days_left <= 6:
        rate = 50
        message = f"체크인 {days_left}일 전 → 50% 환불"
    else:
        rate = 0
        message = f"체크인 {days_left}일 전 → 환불 불가"

    refund_amount = int(total_amount * rate / 100)
    return {
        "refund_rate": rate,
        "refund_amount": refund_amount,
        "days_until_checkin": days_left,
        "message": message,
    }


# ── 토스페이먼츠 인증 ──


def toss_auth_header() -> str:
    """토스페이먼츠 시크릿 키를 Base64 인코딩하여 Basic 인증 헤더 값을 반환합니다.

    토스 API 호출 시 Authorization 헤더에 사용됩니다.
    형식: 'Basic {base64(SECRET_KEY:)}'
    """
    encoded = base64.b64encode(f"{TOSSPAYMENTS_SECRET_KEY}:".encode()).decode()
    return f"Basic {encoded}"
