"""예약 API."""

from fastapi import APIRouter, HTTPException, Query

from config import (
    BASE_WEEKDAY_RATE,
    BASE_WEEKEND_RATE,
    HOLIDAY_DATES,
)
from database import get_db, get_unavailable_date_strings
from models import ReservationCheckRequest
from utils import load_json_object, normalize_phone, parse_date_or_400

router = APIRouter(tags=["reservation"])


@router.get("/api/calendar/config")
async def calendar_config():
    return {
        "holiday_dates": sorted(HOLIDAY_DATES),
        "base_weekday_rate": BASE_WEEKDAY_RATE,
        "base_weekend_rate": BASE_WEEKEND_RATE,
    }


@router.get("/api/calendar/availability")
async def calendar_availability(
    start: str = Query(..., description="조회 시작일(YYYY-MM-DD)"),
    end: str = Query(..., description="조회 종료일(YYYY-MM-DD)"),
):
    start_date = parse_date_or_400(start, "start")
    end_date = parse_date_or_400(end, "end")

    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end는 start 이후 날짜여야 합니다.")
    if (end_date - start_date).days > 730:
        raise HTTPException(status_code=400, detail="조회 기간은 최대 730일입니다.")

    booked_dates = get_unavailable_date_strings(start_date, end_date)

    return {
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "booked_dates": sorted(booked_dates),
    }


@router.post("/api/reservation/check")
async def reservation_check(request: ReservationCheckRequest):
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

    reservation = None
    for candidate in rows:
        if normalize_phone(candidate["customer_phone"]) == phone_digits:
            reservation = dict(candidate)
            break

    if not reservation:
        raise HTTPException(status_code=404, detail="예약 정보를 찾을 수 없습니다.")

    payload = load_json_object(reservation.get("payload"))
    adults = int(payload.get("adults", reservation.get("adults") or 0) or 0)
    bbq = bool(payload.get("bbq", False))
    pet_with = bool(payload.get("pet_with", False))

    return {
        "order_id": reservation["order_id"],
        "status": reservation["status"],
        "checkin_date": reservation["checkin_date"],
        "nights": int(reservation.get("nights") or 1),
        "adults": adults,
        "total_guests": adults,
        "bbq": bbq,
        "pet_with": pet_with,
        "total_amount": int(reservation.get("total_amount") or 0),
        "created_at": reservation["created_at"],
    }
