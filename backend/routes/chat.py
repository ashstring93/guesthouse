"""
챗봇 스트리밍 라우터.

Gemini 2.5 Flash-Lite 기반 AI 챗봇과의 대화를 스트리밍 방식으로 처리합니다.
응답 텍스트에 특정 키워드가 포함되면 관련 이미지를 마크다운으로 자동 첨부합니다.

엔드포인트:
    POST /api/chat → 챗봇 스트리밍 응답
"""

import traceback
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from config import CHATBOT_IMAGE_MAP
from database import log_chat
from models import ChatRequest

router = APIRouter(tags=["chat"])


def _build_image_markdown(answer_text: str) -> str:
    """챗봇 응답 텍스트에서 키워드를 감지하고, 매칭된 이미지의 마크다운을 생성합니다.

    CHATBOT_IMAGE_MAP에 정의된 키워드가 응답에 포함되면
    해당 이미지들을 마크다운 이미지 문법으로 변환합니다.
    중복 이미지는 자동으로 제거됩니다.

    Args:
        answer_text: 챗봇의 전체 응답 텍스트

    Returns:
        마크다운 이미지 문자열 (매칭 없으면 빈 문자열)
    """
    # 이미 추가한 이미지 경로를 추적하여 중복 방지
    seen_paths = set()
    images = []

    for keyword, image_list in CHATBOT_IMAGE_MAP.items():
        if keyword in answer_text:
            for img in image_list:
                if img["path"] not in seen_paths:
                    seen_paths.add(img["path"])
                    # 캡션(📍) + 이미지로 구성하여 사용자가 사진을 구분할 수 있도록 함
                    images.append(
                        f"📍 **{img['alt']}**\n\n![{img['alt']}]({img['path']})"
                    )

    if not images:
        return ""

    # 응답 텍스트와 이미지 사이에 빈 줄로 구분, 각 이미지도 빈 줄로 분리
    return "\n\n" + "\n\n".join(images)


@router.post("/api/chat")
async def chat(request: ChatRequest, http_request: Request):
    """챗봇 스트리밍 엔드포인트.

    사용자 질문을 받아 Gemini 모델에 전달하고,
    응답을 텍스트 스트림으로 실시간 반환합니다.

    챗봇 인스턴스는 app.state.chatbot에서 가져옵니다.
    스트리밍 완료 후:
        1. 키워드 기반 관련 이미지를 마크다운으로 추가
        2. 전체 대화 내용을 DB에 로그로 저장
    """
    # app.state에서 챗봇 인스턴스 가져오기
    chatbot = getattr(http_request.app.state, "chatbot", None)

    if not chatbot:
        raise HTTPException(status_code=503, detail="챗봇이 초기화되지 않았습니다.")

    if not request.question or request.question.strip() == "":
        raise HTTPException(status_code=400, detail="질문을 입력해 주세요.")

    try:
        session_id = request.session_id or str(uuid.uuid4())

        # 스트리밍 응답 생성기 획득 (sources는 미사용)
        generator, _ = chatbot.ask_stream(request.question, session_id)

        # 로그 기록을 위한 스트리밍 래퍼
        # 스트리밍 중 각 청크를 그대로 전달하면서 전체 답변을 축적하고,
        # 스트리밍 완료 후 키워드 이미지를 추가한 뒤 DB에 기록합니다.
        def generator_wrapper(gen, question, sid):
            full_answer = ""
            for chunk in gen:
                full_answer += chunk
                yield chunk

            # 키워드 매칭 이미지가 있으면 마크다운으로 추가 전송
            image_markdown = _build_image_markdown(full_answer)
            if image_markdown:
                yield image_markdown
                full_answer += image_markdown

            log_chat(sid, question, full_answer)

        # 헤더에 세션 ID 포함 → 프론트엔드가 후속 요청에 동일 세션 유지
        headers = {
            "X-Session-Id": session_id,
        }

        return StreamingResponse(
            generator_wrapper(generator, request.question, session_id),
            media_type="text/plain",
            headers=headers,
        )
    except Exception as e:
        traceback.print_exc()
        print(f"Error handling chat request: {e}")
        raise HTTPException(status_code=500, detail=f"오류가 발생했습니다: {str(e)}")