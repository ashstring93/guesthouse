"""
결제 관련 라우터.

요금 견적, 토스 결제 설정, 주문 준비, 결제 성공/실패 콜백을 처리합니다.

엔드포인트:
    POST /api/payment/quote    → 요금 견적
    GET  /api/payment/config   → 토스 클라이언트 키 제공
    POST /api/payment/prepare  → 주문 생성 및 결제 준비
    GET  /reservation/success  → 결제 성공 콜백 (토스 → 서버)
    GET  /reservation/fail     → 결제 실패/취소 콜백
"""

import json
import os

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from config import (
    BBQ_FEE,
    MAX_GUESTS,
    TERMS_VERSION,
    TOSSPAYMENTS_API_BASE,
    TOSSPAYMENTS_SECRET_KEY,
)
from database import get_db, save_payment_intent, save_payment_term_consents
from models import PaymentPrepareRequest, PaymentQuoteRequest
from utils import (
    calculate_extra_guest_details,
    calculate_room_amount,
    create_order_id,
    parse_date_or_400,
    toss_auth_header,
)

router = APIRouter(tags=["payment"])


# ── 요금 견적 ──


@router.post("/api/payment/quote")
async def payment_quote(request: PaymentQuoteRequest):
    """예약 요금 견적.

    체크인 날짜, 숙박 일수, 인원, 옵션을 기반으로
    객실 기본 요금 + 추가 인원 요금 + BBQ 요금을 합산합니다.
    """
    checkin = parse_date_or_400(request.checkin_date)
    nights = max(1, min(request.nights, 5))
    adults = max(0, request.adults)

    if adults <= 0:
        raise HTTPException(
            status_code=400, detail="인원은 최소 1명 이상이어야 합니다."
        )
    if adults > MAX_GUESTS:
        raise HTTPException(
            status_code=400,
            detail=f"인원은 최대 {MAX_GUESTS}명까지 예약할 수 있습니다.",
        )

    room_amount = calculate_room_amount(checkin, nights)
    extra_detail = calculate_extra_guest_details(adults, nights)
    bbq_amount = BBQ_FEE if bool(request.bbq) else 0
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
        "base_weekday_rate": int(os.getenv("BASE_WEEKDAY_RATE", "150000")),
        "base_weekend_rate": int(os.getenv("BASE_WEEKEND_RATE", "200000")),
        "adult_extra_fee": int(os.getenv("ADULT_EXTRA_FEE", "20000")),
        "bbq_fee": BBQ_FEE,
    }


# ── 토스 결제 설정 ──


@router.get("/api/payment/config")
async def payment_config():
    """프론트엔드에 Toss Payments 클라이언트 키를 제공합니다.

    프론트엔드의 결제 위젯 초기화에 필요한 공개 키만 반환합니다.
    시크릿 키는 절대 노출하지 않습니다.
    """
    return {"client_key": os.getenv("TOSSPAYMENTS_WIDGET_CLIENT_KEY", "")}


# ── 주문 생성 ──


@router.post("/api/payment/prepare")
async def payment_prepare(request: PaymentPrepareRequest, http_request: Request):
    """주문 생성 및 결제 준비.

    1. 약관 동의 검증
    2. 요금 계산 (quote와 동일 로직)
    3. DB에 결제 의도(payment_intent) 저장
    4. 약관 동의 기록 저장
    5. 주문번호 + 금액 반환 → 프론트엔드가 토스 결제위젯 호출
    """
    # 필수 약관 동의 확인
    required_consents = {
        "policy": request.agree_policy,
        "privacy": request.agree_privacy,
        "thirdparty": request.agree_thirdparty,
        "adult": request.agree_adult,
    }
    if not request.agreed_to_terms or not all(required_consents.values()):
        raise HTTPException(status_code=400, detail="필수 약관 동의가 필요합니다.")

    term_version = (request.terms_version or TERMS_VERSION).strip() or TERMS_VERSION
    client_ip = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent", "")

    # 요금 계산
    checkin = parse_date_or_400(request.checkin_date)
    nights = max(1, min(request.nights, 5))
    adults = max(0, request.adults)

    if adults <= 0:
        raise HTTPException(
            status_code=400, detail="인원은 최소 1명 이상이어야 합니다."
        )
    if adults > MAX_GUESTS:
        raise HTTPException(
            status_code=400,
            detail=f"인원은 최대 {MAX_GUESTS}명까지 예약할 수 있습니다.",
        )

    room_amount = calculate_room_amount(checkin, nights)
    extra_detail = calculate_extra_guest_details(adults, nights)
    bbq_amount = BBQ_FEE if bool(request.bbq) else 0
    total_amount = room_amount + extra_detail["extra_amount"] + bbq_amount

    # DB 저장
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
        "extra_guests": extra_detail["extra_guests"],
        "room_amount": room_amount,
        "extra_amount": extra_detail["extra_amount"],
        "bbq_amount": bbq_amount,
        "total_amount": total_amount,
        "terms_version": term_version,
        "consents": required_consents,
        "arrival_time": (request.arrival_time or "").strip(),
        "request_note": (request.request_note or "").strip(),
        "client_ip": client_ip,
        "user_agent": user_agent,
        "status": "pending",
    }
    save_payment_intent(intent)
    save_payment_term_consents(order_id, required_consents, term_version, client_ip)

    return {
        "order_id": order_id,
        "amount": total_amount,
        "currency": "KRW",
    }


# ── 결제 성공 콜백 ──


@router.get("/reservation/success")
async def payment_success_page(
    paymentKey: str = Query(...),
    orderId: str = Query(...),
    amount: int = Query(...),
):
    """결제 성공 리다이렉트 핸들러.

    토스 결제위젯이 결제 완료 후 successUrl로 리다이렉트하면,
    paymentKey / orderId / amount 파라미터를 받아
    서버에서 토스 결제 승인 API(POST /v1/payments/confirm)를 호출합니다.
    승인 성공 시 DB 상태를 'paid'로 업데이트하고 성공 페이지를 표시합니다.
    """
    if not TOSSPAYMENTS_SECRET_KEY:
        return HTMLResponse(
            content="<h2>결제 시크릿 키가 설정되지 않았습니다.</h2><p>관리자에게 문의하세요.</p>",
            status_code=500,
        )

    # 토스페이먼츠 결제 승인 API 호출
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
                headers={
                    "Authorization": toss_auth_header(),
                    "Content-Type": "application/json",
                },
            )
    except httpx.RequestError as exc:
        return HTMLResponse(
            content=f"<h2>결제 승인 요청 실패</h2><p>{exc}</p>",
            status_code=502,
        )

    if resp.status_code == 200:
        payment_data = resp.json()

        # DB에 결제 상태 업데이트
        with get_db() as conn:
            conn.execute(
                "UPDATE payment_intents SET status = ?, updated_at = CURRENT_TIMESTAMP, payload = ? WHERE order_id = ?",
                ("paid", json.dumps(payment_data, ensure_ascii=False), orderId),
            )

        # 결제 성공 페이지 렌더링
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
        <div class="order-id">주문번호: {orderId}</div>
        <a href="/">홈으로 돌아가기</a>
    </div>
</body>
</html>
""",
            status_code=200,
        )
    else:
        # 결제 승인 실패
        error_data = (
            resp.json()
            if resp.headers.get("content-type", "").startswith("application/json")
            else {}
        )
        error_code = error_data.get("code", "UNKNOWN")
        error_message = error_data.get("message", "결제 승인에 실패했습니다.")

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
        body {{ font-family: 'Pretendard', sans-serif; background: #fef2f2; display: flex; justify-content: center; align-items: center; min-height: 100vh; }}
        .card {{ background: #fff; border-radius: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); padding: 48px 40px; max-width: 480px; width: 90%; text-align: center; }}
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
        <h1>결제 승인 실패</h1>
        <p>{error_message}</p>
        <div class="error-code">에러 코드: {error_code}</div>
        <a href="/reservation/book.html">다시 시도하기</a>
    </div>
</body>
</html>
""",
            status_code=400,
        )


# ── 결제 실패/취소 콜백 ──


@router.get("/reservation/fail")
async def payment_fail_page(
    code: str = Query(""),
    message: str = Query(""),
    orderId: str = Query(""),
):
    """결제 실패/취소 리다이렉트 핸들러.

    사용자가 결제를 취소하거나 결제 과정에서 에러가 발생한 경우,
    토스 결제위젯이 failUrl로 리다이렉트합니다.
    """
    safe_message = message or "결제가 취소되었거나 실패했습니다."
    safe_code = code or "USER_CANCEL"

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
        <a href="/reservation/book.html">다시 예약하기</a>
    </div>
</body>
</html>
""",
        status_code=200,
    )
