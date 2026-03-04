"""
물레방아하우스 메인 서버 모듈.

FastAPI 앱 생성, 미들웨어 설정, 정적 파일 마운트, 챗봇 수명 관리,
그리고 각 기능별 라우터를 등록합니다.

모듈 구조:
    config.py      → 환경변수, 상수, 경로
    database.py    → DB 초기화, 커넥션, 저장/조회
    models.py      → Pydantic 요청 모델
    utils.py       → 날짜 파싱, 요금 계산, 환불, 토스 인증
    routes/
        pages.py       → HTML 페이지 서빙
        payment.py     → 결제 API
        reservation.py → 캘린더/예약 조회
        admin.py       → 관리자 API
        chat.py        → 챗봇 스트리밍
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from chatbot import GuestHouseChatbot
from config import CORS_ORIGINS, DB_PATH, FRONTEND_DIR, HOLIDAY_DATES
from database import init_db
from routes import admin, chat, pages, payment, reservation


# ── 앱 수명 관리 ──


@asynccontextmanager
async def lifespan(_: FastAPI):
    """서버 시작/종료 시 챗봇 초기화 및 정리.

    서버 시작 시:
        1. DB 테이블 초기화
        2. Gemini API 키 확인
        3. GuestHouseChatbot 인스턴스 생성 → app.state.chatbot에 저장

    서버 종료 시:
        app.state.chatbot을 None으로 정리
    """
    init_db()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경 변수가 설정되어야 합니다.")

    # 챗봇을 app.state에 저장하여 라우터에서 request.app.state.chatbot으로 접근
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


# ── FastAPI 앱 생성 ──


app = FastAPI(
    title="물레방아하우스 챗봇 API",
    description="Gemini 2.5 Flash-Lite 기반 게스트하우스 Q&A 챗봇",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS 미들웨어 ──

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 정적 파일 마운트 ──
# 프론트엔드의 JS, CSS, 이미지, 폰트 파일을 직접 서빙합니다.

app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
app.mount("/images", StaticFiles(directory=str(FRONTEND_DIR / "images")), name="images")
app.mount("/fonts", StaticFiles(directory=str(FRONTEND_DIR / "fonts")), name="fonts")

# ── 라우터 등록 ──
# 각 기능별 라우터를 앱에 포함시킵니다.

app.include_router(pages.router)
app.include_router(payment.router)
app.include_router(reservation.router)
app.include_router(admin.router)
app.include_router(chat.router)


# ── 서버 실행 ──


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
        # reload 모드에서는 import string이 필요합니다.
        uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
    else:
        # 일반 실행은 app 객체를 직접 전달해 모듈 임포트 순서 문제를 피합니다.
        uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
