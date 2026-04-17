"""챗봇 API."""

import json
import traceback
import uuid
from collections.abc import Generator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from config import CHATBOT_IMAGE_MAP
from database import log_chat
from models import ChatRequest

router = APIRouter(tags=["chat"])


def _build_image_markdown(answer_text: str) -> str:
    seen_paths = set()
    images = []

    for keyword, image_list in CHATBOT_IMAGE_MAP.items():
        if keyword in answer_text:
            for img in image_list:
                if img["path"] not in seen_paths:
                    seen_paths.add(img["path"])
                    images.append(
                        f"📍 **{img['alt']}**\n\n![{img['alt']}]({img['path']})"
                    )

    if not images:
        return ""

    return "\n\n" + "\n\n".join(images)


def _sse(event: str, payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=False)
    return f"event: {event}\ndata: {data}\n\n"


def _stream_with_logging(
    generator: Generator[str, None, None],
    question: str,
    session_id: str,
) -> Generator[str, None, None]:
    full_answer = ""

    try:
        yield _sse("session", {"session_id": session_id})

        for chunk in generator:
            full_answer += chunk
            yield _sse("chunk", {"text": chunk})

        image_markdown = _build_image_markdown(full_answer)
        if image_markdown:
            full_answer += image_markdown
            yield _sse("chunk", {"text": image_markdown})

        log_chat(session_id, question, full_answer)
        yield _sse("done", {"session_id": session_id})
    except Exception:
        traceback.print_exc()
        yield _sse(
            "error",
            {"message": "챗봇 응답 생성 중 오류가 발생했습니다."},
        )


@router.post("/api/chat")
async def chat(request: ChatRequest, http_request: Request):
    chatbot = getattr(http_request.app.state, "chatbot", None)

    if not chatbot:
        raise HTTPException(status_code=503, detail="챗봇이 초기화되지 않았습니다.")

    if not request.question or request.question.strip() == "":
        raise HTTPException(status_code=400, detail="질문을 입력해 주세요.")

    try:
        session_id = request.session_id or str(uuid.uuid4())

        generator, _ = chatbot.ask_stream(request.question, session_id)

        headers = {
            "X-Session-Id": session_id,
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        }

        return StreamingResponse(
            _stream_with_logging(generator, request.question, session_id),
            media_type="text/event-stream",
            headers=headers,
        )
    except Exception as e:
        traceback.print_exc()
        print(f"Error handling chat request: {e}")
        raise HTTPException(status_code=500, detail=f"오류가 발생했습니다: {str(e)}")
