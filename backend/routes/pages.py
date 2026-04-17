"""HTML 페이지 라우트."""

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse

from config import FRONTEND_DIR, RESERVATION_PAGES_DIR

LEGAL_PAGES_DIR = FRONTEND_DIR / "pages" / "legal"

router = APIRouter(tags=["pages"])


def _redirect_preserving_query(request: Request, target: str) -> RedirectResponse:
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(url=target, status_code=307)


@router.get("/")
async def root():
    return FileResponse(FRONTEND_DIR / "index.html")


@router.get("/reservation/book")
async def reservation_book_redirect(request: Request):
    return _redirect_preserving_query(request, "book/")


@router.get("/reservation/book/")
async def reservation_book_page():
    return FileResponse(RESERVATION_PAGES_DIR / "book.html")


@router.get("/reservation/list")
async def reservation_list_redirect(request: Request):
    return _redirect_preserving_query(request, "list/")


@router.get("/reservation/list/")
async def reservation_list_page():
    return FileResponse(RESERVATION_PAGES_DIR / "list.html")


@router.get("/reservation/check")
async def reservation_check_redirect(request: Request):
    return _redirect_preserving_query(request, "check/")


@router.get("/reservation/check/")
async def reservation_check_page():
    return FileResponse(RESERVATION_PAGES_DIR / "check.html")


@router.get("/legal/preview")
async def legal_preview_redirect(request: Request):
    return _redirect_preserving_query(request, "preview/")


@router.get("/legal/preview/")
async def legal_preview_page():
    return FileResponse(LEGAL_PAGES_DIR / "preview.html")


@router.get("/reservation-pay.html")
async def reservation_pay_page(request: Request):
    return _redirect_preserving_query(request, "reservation/book/")


@router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse(
        FRONTEND_DIR / "images" / "favicon.ico",
        media_type="image/vnd.microsoft.icon",
    )


@router.get("/api/health")
async def health_check(request: Request):
    chatbot = getattr(request.app.state, "chatbot", None)
    return {"status": "healthy", "chatbot_loaded": chatbot is not None}
