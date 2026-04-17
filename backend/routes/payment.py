"""결제 API."""

import json
from datetime import date, datetime, timedelta
from html import escape

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from config import (
    ADULT_EXTRA_FEE,
    BBQ_FEE,
    BASE_WEEKDAY_RATE,
    BASE_WEEKEND_RATE,
    MAX_GUESTS,
    TERMS_VERSION,
    TOSSPAYMENTS_API_BASE,
    TOSSPAYMENTS_PAYMENT_METHOD_VARIANT_KEY,
    TOSSPAYMENTS_SECRET_KEY,
    TOSSPAYMENTS_WIDGET_CLIENT_KEY,
)
from database import (
    get_db,
    get_stay_unavailable_date_strings,
    save_payment_order,
)
from models import PaymentPrepareRequest, PaymentQuoteRequest
from utils import (
    calculate_extra_guest_details,
    calculate_room_amount,
    create_order_id,
    load_json_object,
    parse_date_or_400,
    toss_auth_header,
)

router = APIRouter(tags=["payment"])
FINAL_BOOKED_STATUSES = ("confirming", "confirmed", "paid")
MAX_NIGHTS = 5
BOOKING_PAGE_PATH = "/reservation/book/"
CHECK_PAGE_PATH = "/reservation/check/"
VIRTUAL_ACCOUNT_METHODS = {"가상계좌", "VIRTUAL_ACCOUNT"}


def _normalize_nights(value: int) -> int:
    return max(1, min(int(value or 1), MAX_NIGHTS))


def _normalize_adults(value: int) -> int:
    return max(0, int(value or 0))


def _validate_guest_count(adults: int):
    if adults <= 0:
        raise HTTPException(
            status_code=400,
            detail="인원은 최소 1명 이상이어야 합니다.",
        )
    if adults > MAX_GUESTS:
        raise HTTPException(
            status_code=400,
            detail=f"인원은 최대 {MAX_GUESTS}명까지 예약할 수 있습니다.",
        )


def _build_quote(checkin: date, nights: int, adults: int, bbq: bool) -> dict:
    room_amount = calculate_room_amount(checkin, nights)
    extra_detail = calculate_extra_guest_details(adults, nights)
    bbq_amount = BBQ_FEE if bbq else 0
    total_amount = room_amount + extra_detail["extra_amount"] + bbq_amount

    return {
        "checkin_date": checkin.isoformat(),
        "nights": nights,
        "adults": adults,
        "total_guests": adults,
        "extra_guests": extra_detail["extra_guests"],
        "room_amount": room_amount,
        "extra_amount": extra_detail["extra_amount"],
        "bbq_amount": bbq_amount,
        "total_amount": total_amount,
        "currency": "KRW",
        "base_weekday_rate": BASE_WEEKDAY_RATE,
        "base_weekend_rate": BASE_WEEKEND_RATE,
        "adult_extra_fee": ADULT_EXTRA_FEE,
        "bbq_fee": BBQ_FEE,
    }


def _required_consents(request: PaymentPrepareRequest) -> dict[str, bool]:
    return {
        "policy": request.agree_policy,
        "privacy": request.agree_privacy,
        "thirdparty": request.agree_thirdparty,
        "adult": request.agree_adult,
    }


def _parse_json_response(resp: httpx.Response) -> dict:
    if not resp.headers.get("content-type", "").startswith("application/json"):
        return {}
    try:
        payload = resp.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _is_virtual_account_payment(payment_data: dict) -> bool:
    method = str(payment_data.get("method") or "").strip()
    return method in VIRTUAL_ACCOUNT_METHODS or bool(payment_data.get("virtualAccount"))


def _toss_headers(idempotency_key: str | None = None) -> dict[str, str]:
    headers = {
        "Authorization": toss_auth_header(),
        "Content-Type": "application/json",
    }
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


async def _cancel_toss_payment(
    client: httpx.AsyncClient,
    payment_key: str,
    cancel_reason: str,
    idempotency_key: str,
) -> dict:
    resp = await client.post(
        f"{TOSSPAYMENTS_API_BASE}/v1/payments/{payment_key}/cancel",
        json={"cancelReason": cancel_reason},
        headers=_toss_headers(idempotency_key),
    )
    if resp.status_code == 200:
        return resp.json()

    error_data = _parse_json_response(resp)
    return {
        "cancel_failed": True,
        "status_code": resp.status_code,
        "error": error_data or {"message": resp.text},
    }


def _ensure_stay_is_available(checkin, nights: int):
    conflict_dates = get_stay_unavailable_date_strings(checkin, nights)
    if not conflict_dates:
        return

    first_conflict = conflict_dates[0]
    raise HTTPException(
        status_code=400,
        detail=(
            "선택한 일정에 이미 예약되었거나 운영상 예약이 막힌 날짜가 포함되어 있습니다. "
            f"(첫 차단 날짜: {first_conflict})"
        ),
    )


def _get_last_stay_date(checkin: date, nights: int) -> date:
    return checkin + timedelta(days=max(1, int(nights or 1)) - 1)


def _reservations_overlap(
    start_a: date, end_a: date, start_b: date, end_b: date
) -> bool:
    return start_a <= end_b and start_b <= end_a


def _build_redirect_payload(order_id: str, payment_key: str, amount: int) -> dict:
    return {
        "paymentKey": payment_key,
        "orderId": order_id,
        "amount": int(amount),
        "payment_redirect": {
            "paymentKey": payment_key,
            "orderId": order_id,
            "amount": int(amount),
            "recordedAt": datetime.now().isoformat(timespec="seconds"),
        },
    }


def _store_payment_redirect_params(
    order_id: str,
    payment_key: str,
    amount: int,
) -> dict | None:
    redirect_payload = _build_redirect_payload(order_id, payment_key, amount)

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT status, payload
            FROM payment_intents
            WHERE order_id = ?
            """,
            (order_id,),
        ).fetchone()

        if not row:
            return None

        payload = load_json_object(row["payload"])
        payload.update(redirect_payload)
        conn.execute(
            """
            UPDATE payment_intents
            SET updated_at = CURRENT_TIMESTAMP, payload = ?
            WHERE order_id = ?
            """,
            (json.dumps(payload, ensure_ascii=False), order_id),
        )

        result = dict(row)
        result["payload"] = payload
        return result


def _update_payment_intent_status(
    order_id: str,
    status: str,
    payload: dict | str | None = None,
):
    serialized_payload = None
    if payload is not None:
        if isinstance(payload, str):
            serialized_payload = payload
        else:
            with get_db() as conn:
                row = conn.execute(
                    "SELECT payload FROM payment_intents WHERE order_id = ?",
                    (order_id,),
                ).fetchone()
                merged_payload = load_json_object(row["payload"] if row else None)
                merged_payload.update(payload)
                serialized_payload = json.dumps(merged_payload, ensure_ascii=False)

    with get_db() as conn:
        if serialized_payload is None:
            conn.execute(
                """
                UPDATE payment_intents
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE order_id = ?
                """,
                (status, order_id),
            )
            return

        conn.execute(
            """
            UPDATE payment_intents
            SET status = ?, updated_at = CURRENT_TIMESTAMP, payload = ?
            WHERE order_id = ?
            """,
            (status, serialized_payload, order_id),
        )


def _claim_payment_for_confirmation(order_id: str, expected_amount: int) -> tuple[str, dict | None]:
    with get_db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """
            SELECT order_id, checkin_date, nights, total_amount, status
            FROM payment_intents
            WHERE order_id = ?
            """,
            (order_id,),
        ).fetchone()

        if not row:
            return "missing", None

        intent = dict(row)
        current_status = str(intent.get("status") or "").lower()
        stored_amount = int(intent.get("total_amount") or 0)

        if current_status == "paid":
            return "already_paid", intent
        if current_status == "confirming":
            return "already_processing", intent
        if current_status != "pending":
            return "invalid_status", intent
        if stored_amount != expected_amount:
            conn.execute(
                """
                UPDATE payment_intents
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE order_id = ?
                """,
                ("failed", order_id),
            )
            return "amount_mismatch", intent

        try:
            checkin = date.fromisoformat(str(intent["checkin_date"]))
            nights = max(1, int(intent.get("nights") or 1))
        except (TypeError, ValueError):
            conn.execute(
                """
                UPDATE payment_intents
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE order_id = ?
                """,
                ("failed", order_id),
            )
            return "invalid_stay", intent

        stay_end = _get_last_stay_date(checkin, nights)
        placeholders = ",".join(["?"] * len(FINAL_BOOKED_STATUSES))
        rows = conn.execute(
            f"""
            SELECT order_id, checkin_date, nights
            FROM payment_intents
            WHERE order_id != ?
              AND lower(status) IN ({placeholders})
            """,
            (order_id, *FINAL_BOOKED_STATUSES),
        ).fetchall()

        for conflict_row in rows:
            try:
                conflict_checkin = date.fromisoformat(str(conflict_row["checkin_date"]))
                conflict_nights = max(1, int(conflict_row["nights"] or 1))
            except (TypeError, ValueError):
                continue

            conflict_end = _get_last_stay_date(conflict_checkin, conflict_nights)
            if _reservations_overlap(checkin, stay_end, conflict_checkin, conflict_end):
                conn.execute(
                    """
                    UPDATE payment_intents
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE order_id = ?
                    """,
                    ("failed", order_id),
                )
                return "date_conflict", intent

        updated = conn.execute(
            """
            UPDATE payment_intents
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE order_id = ? AND lower(status) = 'pending'
            """,
            ("confirming", order_id),
        )
        if updated.rowcount != 1:
            latest = conn.execute(
                """
                SELECT order_id, checkin_date, nights, total_amount, status
                FROM payment_intents
                WHERE order_id = ?
                """,
                (order_id,),
            ).fetchone()
            return "status_changed", dict(latest) if latest else intent

        intent["status"] = "confirming"
        return "ready", intent


def _render_payment_success_page(order_id: str) -> HTMLResponse:
    safe_order_id = escape(order_id)
    return HTMLResponse(
        content=f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>결제 완료 - 물레방아하우스</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Pretendard', sans-serif; background: #f0f4f8; display: flex; justify-content: center; align-items: center; min-height: 100vh; }}
        .card {{ background: #fff; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); padding: 48px 40px; max-width: 480px; width: 90%; text-align: center; }}
        .icon {{ font-size: 64px; margin-bottom: 16px; }}
        h1 {{ font-size: 24px; color: #1a1a1a; margin-bottom: 8px; }}
        p {{ color: #666; line-height: 1.6; margin-bottom: 24px; }}
        .order-id {{ background: #f5f5f5; padding: 12px; border-radius: 8px; font-family: monospace; color: #333; margin-bottom: 24px; }}
        a {{ display: inline-block; padding: 14px 32px; background: #3182f6; color: #fff; text-decoration: none; border-radius: 12px; font-weight: 600; }}
        a:hover {{ background: #1b6cf2; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">✅</div>
        <h1>결제가 완료되었습니다</h1>
        <p>물레방아하우스 예약이 확정되었습니다.<br>감사합니다!</p>
        <div class="order-id">주문번호: {safe_order_id}</div>
        <a href="/">홈으로 돌아가기</a>
    </div>
</body>
</html>
""",
        status_code=200,
    )


def _render_payment_error_page(
    title: str,
    message: str,
    *,
    detail: str = "",
    status_code: int = 400,
    action_href: str = BOOKING_PAGE_PATH,
    action_text: str = "다시 예약하기",
) -> HTMLResponse:
    safe_title = escape(title)
    safe_message = escape(message)
    safe_detail = escape(detail) if detail else ""
    safe_action_href = escape(action_href, quote=True)
    safe_action_text = escape(action_text)
    detail_html = (
        f'<div class="error-code">{safe_detail}</div>'
        if safe_detail
        else ""
    )

    return HTMLResponse(
        content=f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_title} - 물레방아하우스</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Pretendard', sans-serif; background: #fef2f2; display: flex; justify-content: center; align-items: center; min-height: 100vh; }}
        .card {{ background: #fff; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); padding: 48px 40px; max-width: 520px; width: 90%; text-align: center; }}
        .icon {{ font-size: 64px; margin-bottom: 16px; }}
        h1 {{ font-size: 24px; color: #1a1a1a; margin-bottom: 8px; }}
        p {{ color: #666; line-height: 1.6; margin-bottom: 24px; }}
        .error-code {{ background: #fef2f2; padding: 12px; border-radius: 8px; color: #dc2626; margin-bottom: 24px; }}
        a {{ display: inline-block; padding: 14px 32px; background: #3182f6; color: #fff; text-decoration: none; border-radius: 12px; font-weight: 600; }}
        a:hover {{ background: #1b6cf2; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">❌</div>
        <h1>{safe_title}</h1>
        <p>{safe_message}</p>
        {detail_html}
        <a href="{safe_action_href}">{safe_action_text}</a>
    </div>
</body>
</html>
""",
        status_code=status_code,
    )


@router.post("/api/payment/quote")
async def payment_quote(request: PaymentQuoteRequest):
    checkin = parse_date_or_400(request.checkin_date)
    nights = _normalize_nights(request.nights)
    adults = _normalize_adults(request.adults)
    _validate_guest_count(adults)
    _ensure_stay_is_available(checkin, nights)

    return _build_quote(checkin, nights, adults, bool(request.bbq))


@router.get("/api/payment/config")
async def payment_config():
    return {
        "client_key": TOSSPAYMENTS_WIDGET_CLIENT_KEY,
        "payment_method_variant_key": TOSSPAYMENTS_PAYMENT_METHOD_VARIANT_KEY,
    }


@router.post("/api/payment/prepare")
async def payment_prepare(request: PaymentPrepareRequest, http_request: Request):
    required_consents = _required_consents(request)
    if not request.agreed_to_terms or not all(required_consents.values()):
        raise HTTPException(status_code=400, detail="필수 약관 동의가 필요합니다.")

    term_version = (request.terms_version or TERMS_VERSION).strip() or TERMS_VERSION
    client_ip = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent", "")

    checkin = parse_date_or_400(request.checkin_date)
    nights = _normalize_nights(request.nights)
    adults = _normalize_adults(request.adults)
    _validate_guest_count(adults)
    _ensure_stay_is_available(checkin, nights)

    quote = _build_quote(checkin, nights, adults, bool(request.bbq))

    order_id = create_order_id()
    intent = {
        "order_id": order_id,
        "customer_name": request.customer_name.strip(),
        "customer_phone": request.customer_phone.strip(),
        "checkin_date": checkin.isoformat(),
        "nights": nights,
        "adults": adults,
        "total_guests": adults,
        "bbq": bool(request.bbq),
        "pet_with": bool(request.pet_with),
        "extra_guests": quote["extra_guests"],
        "room_amount": quote["room_amount"],
        "extra_amount": quote["extra_amount"],
        "bbq_amount": quote["bbq_amount"],
        "total_amount": quote["total_amount"],
        "terms_version": term_version,
        "consents": required_consents,
        "arrival_time": (request.arrival_time or "").strip(),
        "request_note": (request.request_note or "").strip(),
        "client_ip": client_ip,
        "user_agent": user_agent,
        "status": "pending",
    }
    save_payment_order(intent, required_consents, term_version, client_ip)

    return {
        "order_id": order_id,
        "amount": quote["total_amount"],
        "currency": "KRW",
    }


@router.get("/reservation/success")
async def payment_success_page(
    paymentKey: str = Query(...),
    orderId: str = Query(...),
    amount: int = Query(...),
):
    if not TOSSPAYMENTS_SECRET_KEY:
        return _render_payment_error_page(
            "결제 설정 오류",
            "결제 시크릿 키가 설정되지 않았습니다. 관리자에게 문의해 주세요.",
            status_code=500,
            action_href="/",
            action_text="홈으로 돌아가기",
        )

    redirect_record = _store_payment_redirect_params(orderId, paymentKey, amount)
    if redirect_record is None:
        return _render_payment_error_page(
            "주문 조회 실패",
            "해당 주문을 찾을 수 없습니다. 결제를 다시 진행해 주세요.",
            detail="주문 정보가 서버에 없습니다.",
            status_code=404,
        )

    claim_status, intent = _claim_payment_for_confirmation(orderId, amount)

    if claim_status == "missing":
        return _render_payment_error_page(
            "주문 조회 실패",
            "해당 주문을 찾을 수 없습니다. 결제를 다시 진행해 주세요.",
            detail="주문 정보가 서버에 없습니다.",
            status_code=404,
        )
    if claim_status == "already_paid":
        return _render_payment_success_page(orderId)
    if claim_status == "already_processing":
        return _render_payment_error_page(
            "결제 승인 처리 중",
            "같은 주문의 결제 승인이 이미 진행 중입니다. 잠시 후 예약 조회 화면에서 상태를 확인해 주세요.",
            detail="승인 처리 중에는 중복 승인을 막기 위해 다시 시도할 수 없습니다.",
            status_code=409,
            action_href=CHECK_PAGE_PATH,
            action_text="예약 상태 확인하기",
        )
    if claim_status == "date_conflict":
        return _render_payment_error_page(
            "일정 확보 실패",
            "다른 결제가 먼저 완료 절차에 들어가 선택한 날짜를 확보하지 못했습니다. 이번 결제는 승인하지 않았습니다.",
            detail="브라우저를 닫고 새로운 날짜로 다시 예약해 주세요.",
            status_code=409,
        )
    if claim_status == "amount_mismatch":
        return _render_payment_error_page(
            "결제 금액 검증 실패",
            "서버에 저장된 예약 금액과 결제 승인 요청 금액이 달라 승인을 중단했습니다.",
            detail="브라우저를 새로고침한 뒤 다시 예약해 주세요.",
            status_code=400,
        )
    if claim_status in {"invalid_stay", "invalid_status", "status_changed"}:
        return _render_payment_error_page(
            "결제 상태 확인 실패",
            "현재 주문 상태에서는 결제를 승인할 수 없습니다.",
            detail=f"현재 상태: {(intent or {}).get('status', 'unknown')}",
            status_code=409,
            action_href=CHECK_PAGE_PATH,
            action_text="예약 상태 확인하기",
        )

    confirm_url = f"{TOSSPAYMENTS_API_BASE}/v1/payments/confirm"
    confirm_body = {
        "paymentKey": paymentKey,
        "orderId": orderId,
        "amount": amount,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                confirm_url,
                json=confirm_body,
                headers=_toss_headers(),
            )

            if resp.status_code == 200:
                payment_data = resp.json()

                if _is_virtual_account_payment(payment_data):
                    payment_key_for_cancel = payment_data.get("paymentKey") or paymentKey
                    cancel_data = await _cancel_toss_payment(
                        client,
                        payment_key_for_cancel,
                        "가상계좌 결제수단 미지원",
                        f"reject-virtual-account-{orderId}",
                    )
                    _update_payment_intent_status(
                        orderId,
                        "failed",
                        {
                            "paymentKey": payment_key_for_cancel,
                            "orderId": payment_data.get("orderId", orderId),
                            "amount": amount,
                            "disallowed_payment_method": payment_data,
                            "auto_cancel_response": cancel_data,
                        },
                    )
                    return _render_payment_error_page(
                        "지원하지 않는 결제수단",
                        "가상계좌 결제는 지원하지 않습니다. 카드 또는 간편결제로 다시 예약해 주세요.",
                        detail="가상계좌 결제 요청은 자동 취소 처리했습니다.",
                        status_code=400,
                    )
    except httpx.RequestError as exc:
        _update_payment_intent_status(
            orderId,
            "confirming",
            {"confirm_error": str(exc), "step": "request"},
        )
        return _render_payment_error_page(
            "결제 승인 확인 지연",
            "결제 승인 요청 중 네트워크 오류가 발생했습니다. 중복 결제를 막기 위해 예약은 잠시 승인 대기 상태로 유지됩니다.",
            detail="잠시 후 예약 상태를 확인하거나 관리자에게 문의해 주세요.",
            status_code=502,
            action_href=CHECK_PAGE_PATH,
            action_text="예약 상태 확인하기",
        )

    if resp.status_code == 200:
        payment_data = resp.json()
        _update_payment_intent_status(
            orderId,
            "paid",
            {
                "paymentKey": payment_data.get("paymentKey", paymentKey),
                "orderId": payment_data.get("orderId", orderId),
                "amount": amount,
                "payment_confirm_response": payment_data,
            },
        )
        return _render_payment_success_page(orderId)

    error_data = _parse_json_response(resp)
    error_code = error_data.get("code", "UNKNOWN")
    error_message = error_data.get("message", "결제 승인에 실패했습니다.")

    _update_payment_intent_status(
        orderId,
        "failed",
        {
            "payment_confirm_error": error_data
            or {"code": error_code, "message": error_message}
        },
    )
    return _render_payment_error_page(
        "결제 승인 실패",
        error_message,
        detail=f"에러 코드: {error_code}",
        status_code=400,
    )


@router.get("/reservation/fail")
async def payment_fail_page(
    code: str = Query(""),
    message: str = Query(""),
    orderId: str = Query(""),
    pendingOrderId: str = Query(""),
):
    safe_message = escape(message or "결제가 취소되었거나 실패했습니다.")
    safe_code = escape(code or "USER_CANCEL")
    safe_order_id = (orderId or pendingOrderId or "").strip()

    if safe_order_id:
        failure_status = "cancelled" if code == "PAY_PROCESS_CANCELED" else "failed"
        _update_payment_intent_status(
            safe_order_id,
            failure_status,
            {
                "payment_failure": {
                    "code": code or "USER_CANCEL",
                    "message": message or "결제가 취소되었거나 실패했습니다.",
                    "orderId": orderId or "",
                    "pendingOrderId": pendingOrderId or "",
                    "recordedAt": datetime.now().isoformat(timespec="seconds"),
                }
            },
        )

    return HTMLResponse(
        content=f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>결제 실패 - 물레방아하우스</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Pretendard', sans-serif; background: #fffbeb; display: flex; justify-content: center; align-items: center; min-height: 100vh; }}
        .card {{ background: #fff; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); padding: 48px 40px; max-width: 480px; width: 90%; text-align: center; }}
        .icon {{ font-size: 64px; margin-bottom: 16px; }}
        h1 {{ font-size: 24px; color: #1a1a1a; margin-bottom: 8px; }}
        p {{ color: #666; line-height: 1.6; margin-bottom: 24px; }}
        .error-code {{ background: #fef3c7; padding: 12px; border-radius: 8px; color: #92400e; margin-bottom: 24px; }}
        a {{ display: inline-block; padding: 14px 32px; background: #3182f6; color: #fff; text-decoration: none; border-radius: 12px; font-weight: 600; }}
        a:hover {{ background: #1b6cf2; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">⚠️</div>
        <h1>결제가 완료되지 않았습니다</h1>
        <p>{safe_message}</p>
        <div class="error-code">코드: {safe_code}</div>
        <a href="{BOOKING_PAGE_PATH}">다시 예약하기</a>
    </div>
</body>
</html>
""",
        status_code=200,
    )
