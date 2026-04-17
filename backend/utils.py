"""공통 헬퍼 함수."""

import base64
import json
import uuid
from datetime import date, datetime, timedelta

from fastapi import HTTPException

from config import (
    ADULT_EXTRA_FEE,
    BASE_GUESTS,
    BASE_WEEKDAY_RATE,
    BASE_WEEKEND_RATE,
    TOSSPAYMENTS_SECRET_KEY,
)


def _is_weekend_rate_day(target: date) -> bool:
    return target.weekday() in (4, 5)


def _room_rate_for_date(target: date) -> int:
    return BASE_WEEKEND_RATE if _is_weekend_rate_day(target) else BASE_WEEKDAY_RATE


def create_order_id() -> str:
    """주문번호를 만듭니다."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"MBA-{timestamp}-{uuid.uuid4().hex[:6].upper()}"


def parse_date_or_400(date_str: str, field_name: str = "checkin_date") -> date:
    """YYYY-MM-DD 날짜를 파싱합니다."""
    try:
        return datetime.strptime(str(date_str), "%Y-%m-%d").date()
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} 형식이 올바르지 않습니다. (YYYY-MM-DD)",
        ) from exc


def normalize_phone(value: str) -> str:
    """전화번호에서 숫자만 남깁니다."""
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def load_json_object(raw_payload) -> dict:
    """JSON 객체 문자열을 dict로 읽습니다."""
    if not raw_payload:
        return {}

    try:
        payload = json.loads(raw_payload)
    except (TypeError, json.JSONDecodeError):
        return {}

    return payload if isinstance(payload, dict) else {}


def calculate_room_amount(checkin_date: date, nights: int) -> int:
    """숙박일수 기준 객실 요금."""
    return sum(
        _room_rate_for_date(checkin_date + timedelta(days=offset))
        for offset in range(nights)
    )


def calculate_extra_guest_details(adults: int, nights: int) -> dict:
    """추가 인원 수와 요금."""
    extra_guests = max(0, adults - BASE_GUESTS)
    extra_amount = extra_guests * ADULT_EXTRA_FEE * max(1, nights)

    return {
        "extra_guests": extra_guests,
        "extra_amount": extra_amount,
    }


def calculate_refund_amount(checkin_date_str: str, total_amount: int) -> dict:
    """체크인까지 남은 날짜로 환불 금액을 계산합니다."""
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


def toss_auth_header() -> str:
    """토스 API Basic 인증 헤더."""
    encoded = base64.b64encode(f"{TOSSPAYMENTS_SECRET_KEY}:".encode()).decode()
    return f"Basic {encoded}"
