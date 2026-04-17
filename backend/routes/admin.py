"""관리자 API."""

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
from database import (
    delete_admin_date_block,
    get_db,
    list_admin_date_blocks,
    upsert_admin_date_block,
)
from models import AdminDateBlockRequest, CancelPaymentRequest
from utils import (
    calculate_refund_amount,
    load_json_object,
    parse_date_or_400,
    toss_auth_header,
)

router = APIRouter(tags=["admin"])
CANCELLED_STATUSES = {"cancelled", "refunded"}


def _verify_admin_token(token: str):
    if not ADMIN_TOKEN or token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="관리자 인증에 실패했습니다.")


def _extract_payment_key(order: dict) -> str:
    return str(load_json_object(order.get("payload")).get("paymentKey", ""))


def _mark_order_cancelled(
    order_id: str,
    cancel_reason: str,
    payload: dict | None = None,
):
    serialized_payload = json.dumps(payload, ensure_ascii=False) if payload else None

    with get_db() as conn:
        if serialized_payload is None:
            conn.execute(
                """
                UPDATE payment_intents
                SET status = ?,
                    updated_at = CURRENT_TIMESTAMP,
                    cancel_reason = ?,
                    cancelled_at = CURRENT_TIMESTAMP
                WHERE order_id = ?
                """,
                ("cancelled", cancel_reason, order_id),
            )
            return

        conn.execute(
            """
            UPDATE payment_intents
            SET status = ?,
                updated_at = CURRENT_TIMESTAMP,
                cancel_reason = ?,
                cancelled_at = CURRENT_TIMESTAMP,
                payload = ?
            WHERE order_id = ?
            """,
            ("cancelled", cancel_reason, serialized_payload, order_id),
        )


def _build_cancel_body(cancel_reason: str, refund_info: dict) -> dict:
    body = {"cancelReason": cancel_reason}
    if refund_info["refund_rate"] < 100:
        body["cancelAmount"] = refund_info["refund_amount"]
    return body


def _parse_toss_error(resp: httpx.Response) -> dict:
    if not resp.headers.get("content-type", "").startswith("application/json"):
        return {}
    try:
        return resp.json()
    except ValueError:
        return {}


def _cancel_idempotency_key(order_id: str, refund_info: dict) -> str:
    return f"cancel-{order_id}-{refund_info['refund_amount']}"


@router.get("/api/admin/date-blocks")
async def admin_list_date_blocks(token: str = Query("")):
    _verify_admin_token(token)
    return {"date_blocks": list_admin_date_blocks()}


@router.post("/api/admin/date-blocks")
async def admin_create_date_block(
    request: AdminDateBlockRequest,
    token: str = Query(""),
):
    _verify_admin_token(token)

    start_date = parse_date_or_400(request.start_date, "start_date")
    end_date = parse_date_or_400(
        request.end_date or request.start_date,
        "end_date",
    )

    if end_date < start_date:
        raise HTTPException(
            status_code=400,
            detail="end_date는 start_date 이후 또는 같은 날짜여야 합니다.",
        )

    date_block = upsert_admin_date_block(
        start_date.isoformat(),
        end_date.isoformat(),
        request.reason.strip(),
    )
    return {"success": True, "date_block": date_block}


@router.delete("/api/admin/date-blocks/{block_id}")
async def admin_remove_date_block(block_id: int, token: str = Query("")):
    _verify_admin_token(token)

    if block_id <= 0:
        raise HTTPException(status_code=400, detail="유효한 차단 일정 ID가 필요합니다.")

    deleted = delete_admin_date_block(block_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="해당 차단 일정을 찾을 수 없습니다.")

    return {"success": True}


@router.get("/api/admin/reservations")
async def admin_list_reservations(token: str = Query("")):
    _verify_admin_token(token)

    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM payment_intents ORDER BY created_at DESC"
        ).fetchall()

    results = []
    for row in rows:
        item = dict(row)
        refund_info = calculate_refund_amount(
            item.get("checkin_date", ""), item.get("total_amount", 0)
        )
        item["refund_info"] = refund_info

        item["payment_key"] = _extract_payment_key(item)
        results.append(item)

    return {"reservations": results}


@router.post("/api/admin/cancel-payment")
async def admin_cancel_payment(
    request: CancelPaymentRequest,
    token: str = Query(""),
):
    _verify_admin_token(token)

    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM payment_intents WHERE order_id = ?", (request.order_id,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="해당 주문을 찾을 수 없습니다.")

    order = dict(row)

    if order.get("status") in CANCELLED_STATUSES:
        raise HTTPException(status_code=400, detail="이미 취소된 주문입니다.")

    if order.get("status") != "paid":
        raise HTTPException(
            status_code=400,
            detail=f"결제 완료 상태가 아닙니다. (현재: {order.get('status')})",
        )

    payment_key = _extract_payment_key(order)
    if not payment_key:
        raise HTTPException(
            status_code=400,
            detail="결제 키(paymentKey)를 찾을 수 없습니다. 토스 상점관리자에서 직접 취소해 주세요.",
        )

    refund_info = calculate_refund_amount(
        order.get("checkin_date", ""), order.get("total_amount", 0)
    )

    if refund_info["refund_amount"] <= 0:
        raise HTTPException(status_code=400, detail=refund_info["message"])

    cancel_url = f"{TOSSPAYMENTS_API_BASE}/v1/payments/{payment_key}/cancel"
    cancel_body = _build_cancel_body(request.cancel_reason, refund_info)

    if not TOSSPAYMENTS_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="토스 시크릿 키가 없어 결제 취소 API를 호출할 수 없습니다.",
        )

    try:
        headers = {
            "Authorization": toss_auth_header(),
            "Content-Type": "application/json",
            "Idempotency-Key": _cancel_idempotency_key(request.order_id, refund_info),
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                cancel_url,
                json=cancel_body,
                headers=headers,
            )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"토스 결제 취소 요청 실패: {exc}")

    if resp.status_code == 200:
        _mark_order_cancelled(request.order_id, request.cancel_reason, resp.json())
        return {
            "success": True,
            "message": f"결제 취소 완료 (환불: {refund_info['refund_amount']:,}원)",
            "refund_info": refund_info,
        }

    error_data = _parse_toss_error(resp)
    raise HTTPException(
        status_code=resp.status_code,
        detail=(
            "토스 결제 취소 실패: "
            f"{error_data.get('message', '알 수 없는 오류')} "
            f"(코드: {error_data.get('code', 'UNKNOWN')})"
        ),
    )


@router.get("/admin/dashboard")
async def admin_dashboard_page():
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
