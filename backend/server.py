"""물레방아하우스 챗봇 FastAPI 서버."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from chatbot import GuestHouseChatbot

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# 루트 .env와 backend/.env를 모두 읽되 backend 값을 우선합니다.
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env", override=True)

chatbot = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize and clean up chatbot lifecycle."""
    global chatbot
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")

    chroma_persist_directory = os.getenv("CHROMA_PERSIST_DIRECTORY")
    chatbot = GuestHouseChatbot(
        api_key=api_key,
        chroma_persist_directory=chroma_persist_directory,
    )
    print("챗봇 초기화 완료")
    print("  model: gemini-2.5-flash-lite")
    print("  vector_db: ChromaDB")

    try:
        yield
    finally:
        chatbot = None


app = FastAPI(
    title="물레방아하우스 챗봇 API",
    description="Gemini 2.5 Flash-Lite 기반 게스트하우스 Q&A 챗봇",
    version="1.0.0",
    lifespan=lifespan,
)

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8000").split(",")
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


class ChatRequest(BaseModel):
    question: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"question": "체크인 시간이 언제인가요?"}}
    )


class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: list[str]


@app.get("/")
async def root():
    """웹사이트 메인 페이지."""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health")
async def health_check():
    """헬스체크."""
    return {"status": "healthy", "chatbot_loaded": chatbot is not None}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """챗봇 대화 엔드포인트."""
    if not chatbot:
        raise HTTPException(status_code=503, detail="챗봇이 초기화되지 않았습니다.")

    if not request.question or request.question.strip() == "":
        raise HTTPException(status_code=400, detail="질문을 입력해주세요.")

    try:
        result = chatbot.ask(request.question)
        return ChatResponse(
            question=result["question"],
            answer=result["answer"],
            sources=result["sources"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"오류가 발생했습니다: {str(e)}")


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
    print("=" * 70)

    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=reload_enabled)
