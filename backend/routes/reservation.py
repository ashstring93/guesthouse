"""
예약 관련 라우터.

캘린더 설정, 예약 가능일 조회, 예약 정보 확인 엔드포인트를 제공합니다.

엔드포인트:
    GET  /api/calendar/config       → 캘린더 요금/공휴일 설정
    GET  /api/calendar/availability → 예약 마감일 목록
    POST /api/reservation/check     → 예약자명 + 연락처로 예약 조회
"""

import json
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query

from config import (
    BASE_WEEKDAY_RATE,
    BASE_WEEKEND_RATE,
    BOOKED_STATUS_FILTER,
    HOLIDAY_DATES,
)
from database import get_db
from models import ReservationCheckRequest
from utils import normalize_phone, parse_date_or_400

router = APIRouter(tags=["reservation"])


# ── 캘린더 설정 ──


@router.get("/api/calendar/config")
async def calendar_config():
    """캘린더 요금 기본값과 공휴일 설정.

    프론트엔드 캘린더에 공휴일 강조 표시와 요금 안내를 위해 사용됩니다.
    """
    return {
        "holiday_dates": sorted(HOLIDAY_DATES),
        "base_weekday_rate": BASE_WEEKDAY_RATE,
        "base_weekend_rate": BASE_WEEKEND_RATE,
    }


# ── 예약 가능일 조회 ──


@router.get("/api/calendar/availability")
async def calendar_availability(
    start: str = Query(..., description="조회 시작일(YYYY-MM-DD)"),
    end: str = Query(..., description="조회 종료일(YYYY-MM-DD)"),
):
    """예약 현황 달력용 마감일 목록.

    지정된 기간 내에서 이미 예약(pending/confirmed/paid)된 날짜를 반환합니다.
    프론트엔드 캘린더에서 해당 날짜를 마감 표시하는 데 사용됩니다.
    """
    start_date = parse_date_or_400(start, "start")
    end_date = parse_date_or_400(end, "end")

    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end는 start 이후 날짜여야 합니다.")
    if (end_date - start_date).days > 730:
        raise HTTPException(status_code=400, detail="조회 기간은 최대 730일입니다.")

    # DB에서 예약 건을 조회하여 체크인~체크아웃 범위의 날짜를 수집
    query = """
        SELECT checkin_date, nights, status
        FROM payment_intents
        WHERE checkin_date IS NOT NULL
          AND nights IS NOT NULL
    """
    params: list[str] = []
    if BOOKED_STATUS_FILTER:
        placeholders = ",".join(["?"] * len(BOOKED_STATUS_FILTER))
        query += f" AND lower(status) IN ({placeholders})"
        params.extend(BOOKED_STATUS_FILTER)

    booked_dates: set[str] = set()
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()

    for checkin_str, nights_value, _status in rows:
        try:
            checkin = datetime.strptime(str(checkin_str), "%Y-%m-%d").date()
            nights = int(nights_value)
        except (ValueError, TypeError):
            continue

        if nights <= 0:
            continue

        # 체크인부터 숙박 일수만큼의 각 날짜를 마감 목록에 추가
        for offset in range(nights):
            target = checkin + timedelta(days=offset)
            if start_date <= target <= end_date:
                booked_dates.add(target.isoformat())

    return {
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "booked_dates": sorted(booked_dates),
    }


# ── 예약 조회 ──


@router.post("/api/reservation/check")
async def reservation_check(request: ReservationCheckRequest):
    """예약자명 + 연락처로 최신 예약 건을 조회합니다.

    이름이 일치하는 예약을 최신순으로 검색한 후,
    연락처(숫자만 비교)가 일치하는 첫 번째 건을 반환합니다.
    """
    customer_name = request.customer_name.strip()
    phone_digits = normalize_phone(request.customer_phone)

    if not customer_name:
        raise HTTPException(status_code=400, detail="customer_name을 입력해 주세요.")
    if not phone_digits:
        raise HTTPException(status_code=400, detail="customer_phone을 입력해 주세요.")

    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT order_id, status, checkin_date, nights, adults, total_amount,
                   created_at, customer_phone, payload
            FROM payment_intents
            WHERE trim(customer_name) = ?
            ORDER BY id DESC
        """,
            (customer_name,),
        ).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="예약 정보를 찾을 수 없습니다.")

    # 연락처가 일치하는 예약 건 검색
    row = None
    for candidate in rows:
        if normalize_phone(candidate[7]) == phone_digits:
            row = candidate
            break

    if not row:
        raise HTTPException(status_code=404, detail="예약 정보를 찾을 수 없습니다.")

    (
        found_order_id,
        status,
        checkin_date,
        nights,
        total_guests,
        total_amount,
        created_at,
        _customer_phone,
        payload_raw,
    ) = row

    # payload에서 추가 정보(adults, bbq, pet_with) 추출
    payload = {}
    if payload_raw:
        try:
            payload = json.loads(payload_raw)
        except (TypeError, json.JSONDecodeError):
            payload = {}

    adults = int(payload.get("adults", total_guests or 0) or 0)
    bbq = bool(payload.get("bbq", False))
    pet_with = bool(payload.get("pet_with", False))

    return {
        "order_id": found_order_id,
        "status": status,
        "checkin_date": checkin_date,
        "nights": int(nights or 1),
        "adults": adults,
        "total_guests": adults,
        "bbq": bbq,
        "pet_with": pet_with,
        "total_amount": int(total_amount or 0),
        "created_at": created_at,
    }
