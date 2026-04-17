"""FastAPI 앱 진입점."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from chatbot import GuestHouseChatbot
from config import CORS_ORIGINS, DB_PATH, FRONTEND_DIR, HOLIDAY_DATES
from database import init_db
from routes import admin, chat, pages, payment, reservation


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경 변수가 설정되어야 합니다.")

    app.state.chatbot = GuestHouseChatbot(api_key=api_key)
    print("챗봇 초기화 완료")
    print("  model: gemini-2.5-flash-lite")
    print("  RAG 기반 문서 컨텍스트 로드 완료")
    print(f"  DB 로그 경로: {DB_PATH}")
    print(f"  holiday count: {len(HOLIDAY_DATES)} (manual)")

    try:
        yield
    finally:
        app.state.chatbot = None


app = FastAPI(
    title="물레방아하우스 챗봇 API",
    description="Gemini 2.5 Flash-Lite 기반 게스트하우스 Q&A 챗봇",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
app.mount("/images", StaticFiles(directory=str(FRONTEND_DIR / "images")), name="images")
app.mount("/fonts", StaticFiles(directory=str(FRONTEND_DIR / "fonts")), name="fonts")

app.include_router(pages.router)
app.include_router(payment.router)
app.include_router(reservation.router)
app.include_router(admin.router)
app.include_router(chat.router)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    reload_enabled = os.getenv("UVICORN_RELOAD", "false").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    print("=" * 70)
    print("물레방아하우스 챗봇 서버 시작")
    print("=" * 70)
    print(f"  port: {port}")
    print(f"  docs: http://localhost:{port}/docs")
    print(f"  reload: {reload_enabled}")
    print(f"  frontend: {FRONTEND_DIR}")
    print("  static: /js, /css, /images, /fonts")
    print("=" * 70)

    if reload_enabled:
        uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
    else:
        uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
