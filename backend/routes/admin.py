"""
관리자 API 라우터.

예약 목록 조회, 결제 취소(환불 정책 자동 적용), 관리자 대시보드 페이지를 제공합니다.
모든 관리자 API는 token 쿼리 파라미터로 인증합니다.

엔드포인트:
    GET  /api/admin/reservations    → 전체 예약 목록 + 환불 예상 금액
    POST /api/admin/cancel-payment  → 결제 취소 (환불 정책 적용)
    GET  /admin/dashboard           → 관리자 대시보드 HTML 페이지
"""

import json

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse

from config import (
    ADMIN_TOKEN,
    FRONTEND_DIR,
    TOSSPAYMENTS_API_BASE,
    TOSSPAYMENTS_SECRET_KEY,
)
from database import get_db
from models import CancelPaymentRequest
from utils import calculate_refund_amount, toss_auth_header

router = APIRouter(tags=["admin"])


# ── 인증 헬퍼 ──


def _verify_admin_token(token: str):
    """관리자 토큰 검증.

    환경변수 ADMIN_DASHBOARD_TOKEN과 비교하여,
    토큰이 설정되지 않았거나 불일치 시 403 에러를 발생시킵니다.
    """
    if not ADMIN_TOKEN or token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="관리자 인증에 실패했습니다.")


# ── 예약 목록 조회 ──


@router.get("/api/admin/reservations")
async def admin_list_reservations(token: str = Query("")):
    """관리자용: 전체 예약 목록 + 환불 예상 금액 조회.

    각 예약 건에 대해 환불 정책 기반 환불 예상 정보와
    결제 완료 건의 paymentKey를 함께 반환합니다.
    """
    _verify_admin_token(token)

    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM payment_intents ORDER BY created_at DESC"
        ).fetchall()

    results = []
    for row in rows:
        item = dict(row)
        # 환불 예상 정보 계산
        refund_info = calculate_refund_amount(
            item.get("checkin_date", ""), item.get("total_amount", 0)
        )
        item["refund_info"] = refund_info

        # payload에서 paymentKey 추출 (결제 완료된 건에 한함)
        payment_key = ""
        if item.get("payload"):
            try:
                payload_data = json.loads(item["payload"])
                payment_key = payload_data.get("paymentKey", "")
            except (json.JSONDecodeError, TypeError):
                pass
        item["payment_key"] = payment_key
        results.append(item)

    return {"reservations": results}


# ── 결제 취소 ──


@router.post("/api/admin/cancel-payment")
async def admin_cancel_payment(
    request: CancelPaymentRequest,
    token: str = Query(""),
):
    """관리자용: 결제 취소 (환불 정책 자동 적용).

    1. DB에서 주문 조회 및 상태 검증
    2. paymentKey 추출
    3. 환불 금액 계산 (체크인 잔여일 기준)
    4. 토스페이먼츠 결제 취소 API 호출
    5. DB 상태 업데이트
    """
    _verify_admin_token(token)

    # 1. DB에서 주문 조회
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM payment_intents WHERE order_id = ?", (request.order_id,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="해당 주문을 찾을 수 없습니다.")

    order = dict(row)

    if order.get("status") in ("cancelled", "refunded"):
        raise HTTPException(status_code=400, detail="이미 취소된 주문입니다.")

    if order.get("status") != "paid":
        raise HTTPException(
            status_code=400,
            detail=f"결제 완료 상태가 아닙니다. (현재: {order.get('status')})",
        )

    # 2. paymentKey 추출
    payment_key = ""
    if order.get("payload"):
        try:
            payload_data = json.loads(order["payload"])
            payment_key = payload_data.get("paymentKey", "")
        except (json.JSONDecodeError, TypeError):
            pass

    if not payment_key:
        raise HTTPException(
            status_code=400,
            detail="결제 키(paymentKey)를 찾을 수 없습니다. 토스 상점관리자에서 직접 취소해 주세요.",
        )

    # 3. 환불 금액 계산
    refund_info = calculate_refund_amount(
        order.get("checkin_date", ""), order.get("total_amount", 0)
    )

    if refund_info["refund_amount"] <= 0:
        raise HTTPException(status_code=400, detail=refund_info["message"])

    # 4. 토스페이먼츠 결제 취소 API 호출
    cancel_url = f"{TOSSPAYMENTS_API_BASE}/v1/payments/{payment_key}/cancel"
    cancel_body = {"cancelReason": request.cancel_reason}

    # 부분 환불인 경우 cancelAmount 지정
    if refund_info["refund_rate"] < 100:
        cancel_body["cancelAmount"] = refund_info["refund_amount"]

    if not TOSSPAYMENTS_SECRET_KEY:
        # 시크릿 키가 없을 때는 DB 상태만 업데이트 (테스트/개발 환경용)
        with get_db() as conn:
            conn.execute(
                "UPDATE payment_intents SET status = ?, updated_at = CURRENT_TIMESTAMP, cancel_reason = ?, cancelled_at = CURRENT_TIMESTAMP WHERE order_id = ?",
                ("cancelled", request.cancel_reason, request.order_id),
            )

        return {
            "success": True,
            "message": "시크릿 키 미설정 → DB 상태만 cancelled로 변경 (토스 API 미호출)",
            "refund_info": refund_info,
        }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                cancel_url,
                json=cancel_body,
                headers={
                    "Authorization": toss_auth_header(),
                    "Content-Type": "application/json",
                },
            )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"토스 결제 취소 요청 실패: {exc}")

    if resp.status_code == 200:
        cancel_data = resp.json()
        # 5. DB 상태 업데이트
        with get_db() as conn:
            conn.execute(
                "UPDATE payment_intents SET status = ?, updated_at = CURRENT_TIMESTAMP, cancel_reason = ?, cancelled_at = CURRENT_TIMESTAMP, payload = ? WHERE order_id = ?",
                (
                    "cancelled",
                    request.cancel_reason,
                    json.dumps(cancel_data, ensure_ascii=False),
                    request.order_id,
                ),
            )

        return {
            "success": True,
            "message": f"결제 취소 완료 (환불: {refund_info['refund_amount']:,}원)",
            "refund_info": refund_info,
        }
    else:
        error_data = (
            resp.json()
            if resp.headers.get("content-type", "").startswith("application/json")
            else {}
        )
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"토스 결제 취소 실패: {error_data.get('message', '알 수 없는 오류')} (코드: {error_data.get('code', 'UNKNOWN')})",
        )


# ── 관리자 대시보드 페이지 ──


@router.get("/admin/dashboard")
async def admin_dashboard_page():
    """관리자 대시보드 페이지.

    admin-dashboard.html 파일을 서빙합니다.
    파일이 없을 경우 404 에러 페이지를 표시합니다.
    """
    admin_html = FRONTEND_DIR / "pages" / "admin" / "admin-dashboard.html"
    if not admin_html.exists():
        return HTMLResponse(
            content="<h2>관리자 대시보드 페이지가 존재하지 않습니다.</h2>",
            status_code=404,
        )
    return FileResponse(
        admin_html,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )
