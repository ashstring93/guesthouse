"""
물레방아하우스 챗봇 백엔드 FastAPI 서버
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from chatbot import GuestHouseChatbot

load_dotenv()

# FastAPI 앱 초기화
app = FastAPI(
    title="물레방아하우스 챗봇 API",
    description="Gemini 2.5 Flash-Lite 기반 게스트하우스 Q&A 챗봇",
    version="1.0.0",
)

# CORS 설정
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 마운트 (프론트엔드 서빙)
app.mount("/js", StaticFiles(directory="../js"), name="js")
app.mount("/css", StaticFiles(directory="../css"), name="css")
# app.mount("/images", StaticFiles(directory="../images"), name="images")

# 챗봇 인스턴스 (앱 시작 시 한 번만 로드)
chatbot = None


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 챗봇 초기화"""
    global chatbot
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")

    chatbot = GuestHouseChatbot(api_key=api_key)
    print("✅ 챗봇 초기화 완료")
    print(f"   모델: gemini-2.5-flash-lite")
    print(f"   벡터 DB: ChromaDB")


# 요청/응답 모델
class ChatRequest(BaseModel):
    question: str

    class Config:
        json_schema_extra = {"example": {"question": "체크인 시간이 언제인가요?"}}


class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: list[str]


# API 엔드포인트
@app.get("/")
async def root():
    """웹사이트 메인 페이지 (index.html)"""
    return FileResponse("../index.html")


@app.get("/api/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "chatbot_loaded": chatbot is not None}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """챗봇 대화 엔드포인트"""
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

    print("=" * 70)
    print("🚀 물레방아하우스 챗봇 서버 시작")
    print("=" * 70)
    print(f"   포트: {port}")
    print(f"   문서: http://localhost:{port}/docs")
    print("=" * 70)

    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
