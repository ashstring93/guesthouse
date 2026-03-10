"""
페이지 서빙 라우터.

HTML 페이지 파일 응답, 예약 페이지 리다이렉트, favicon 처리,
그리고 헬스체크 엔드포인트를 제공합니다.

엔드포인트:
    GET  /                      → 메인 페이지
    GET  /reservation/book      → 예약/결제 페이지 (리다이렉트)
    GET  /reservation/book/     → 예약/결제 페이지
    GET  /reservation/list      → 예약 현황 페이지 (리다이렉트)
    GET  /reservation/list/     → 예약 현황 페이지
    GET  /reservation/check     → 예약 확인 페이지 (리다이렉트)
    GET  /reservation/check/    → 예약 확인 페이지
    GET  /reservation-pay.html  → 구형 경로 호환 리다이렉트
    GET  /favicon.ico           → 빈 응답 (204)
    GET  /api/health            → 서버 상태 확인
"""

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse

from config import FRONTEND_DIR, RESERVATION_PAGES_DIR

LEGAL_PAGES_DIR = FRONTEND_DIR / "pages" / "legal"

# prefix 없이 루트 경로에 마운트됩니다.
router = APIRouter(tags=["pages"])


@router.get("/")
async def root():
    """웹사이트 메인 페이지."""
    return FileResponse(FRONTEND_DIR / "index.html")


# ── 예약/결제 페이지 ──
# 슬래시 없는 URL → 슬래시 URL로 정규화(307 리다이렉트)합니다.
# 이렇게 하면 브라우저의 상대 경로 해석이 일관됩니다.


@router.get("/reservation/book")
async def reservation_book_redirect(request: Request):
    """예약/결제 페이지 슬래시 URL로 정규화."""
    target = "book/"
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(url=target, status_code=307)


@router.get("/reservation/book/")
async def reservation_book_page():
    """예약/결제용 페이지."""
    return FileResponse(RESERVATION_PAGES_DIR / "book.html")


# ── 예약 현황 페이지 ──


@router.get("/reservation/list")
async def reservation_list_redirect(request: Request):
    """예약 현황 페이지 슬래시 URL로 정규화."""
    target = "list/"
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(url=target, status_code=307)


@router.get("/reservation/list/")
async def reservation_list_page():
    """예약 현황 페이지."""
    return FileResponse(RESERVATION_PAGES_DIR / "list.html")


# ── 예약 확인 페이지 ──


@router.get("/reservation/check")
async def reservation_check_redirect(request: Request):
    """예약 확인 페이지 슬래시 URL로 정규화."""
    target = "check/"
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(url=target, status_code=307)


@router.get("/reservation/check/")
async def reservation_check_page():
    """예약 확인 페이지."""
    return FileResponse(RESERVATION_PAGES_DIR / "check.html")


@router.get("/legal/preview")
async def legal_preview_redirect(request: Request):
    """약관/개인정보 처리방침 초안 페이지를 슬래시 경로로 정규화합니다."""
    target = "preview/"
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(url=target, status_code=307)


@router.get("/legal/preview/")
async def legal_preview_page():
    """약관·개인정보 처리방침 검토용 초안 페이지."""
    return FileResponse(LEGAL_PAGES_DIR / "preview.html")


# ── 구형 경로 호환 ──


@router.get("/reservation-pay.html")
async def reservation_pay_page(request: Request):
    """구형 예약 경로 호환용 리다이렉트.

    과거 '/reservation-pay.html' 경로로 접근하는 사용자를
    새 경로 '/reservation/book/'로 자동 안내합니다.
    """
    target = "reservation/book/"
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(url=target, status_code=307)


# ── 기타 ──


@router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Favicon 404 에러 방지를 위한 빈 응답."""
    return FileResponse(
        FRONTEND_DIR / "images" / "favicon.ico",
        media_type="image/vnd.microsoft.icon",
    )


@router.get("/api/health")
async def health_check(request: Request):
    """헬스체크 엔드포인트.

    서버 상태와 챗봇 초기화 여부를 반환합니다.
    """
    chatbot = getattr(request.app.state, "chatbot", None)
    return {"status": "healthy", "chatbot_loaded": chatbot is not None}
