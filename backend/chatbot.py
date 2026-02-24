from pathlib import Path
from typing import Generator
from google import genai
from google.genai import types

BACKEND_DIR = Path(__file__).resolve().parent
KNOWLEDGE_BASE_FILE = BACKEND_DIR / "knowledge_base" / "integrated_accommodation_guide.md"
DEFAULT_MODEL = "gemini-2.5-flash-lite"


def _load_knowledge_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Knowledge base file not found: {path}")
        return "숙소 기본 안내 정보가 준비되지 않았습니다."


def _build_system_instruction(knowledge_text: str) -> str:
    return (
        "당신은 전주 물레방아하우스 숙소 안내 챗봇입니다.\n"
        "아래 숙소 안내 문서를 근거로 정확하고 친절하게 답변하세요.\n\n"
        "[숙소 안내 문서]\n"
        f"{knowledge_text}\n\n"
        "[답변 규칙]\n"
        "1) 문서에 있는 사실만 우선 답변합니다.\n"
        "2) 가격, 인원, 시간은 숫자를 분명하게 적습니다.\n"
        "3) 문서에 없는 내용은 모른다고 말하고 숙소 문의를 안내합니다.\n"
        "4) 직전 대화 맥락을 반영해 자연스럽게 이어서 답변합니다.\n"
        "5) 읽기 쉬운 마크다운 문장/목록 형태를 사용합니다.\n"
    )


class GuestHouseChatbot:
    """Stateful chatbot wrapper with per-session chat history."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        if not api_key:
            raise ValueError("api_key is required")

        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.knowledge_text = _load_knowledge_text(KNOWLEDGE_BASE_FILE)
        self.system_instruction = _build_system_instruction(self.knowledge_text)
        self._sessions: dict[str, object] = {}

    def _get_or_create_session(self, session_id: str):
        session = self._sessions.get(session_id)
        if session is None:
            session = self.client.chats.create(
                model=self.model,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.7,
                    max_output_tokens=1024,
                ),
            )
            self._sessions[session_id] = session
        return session

    def ask_stream(
        self,
        question: str,
        session_id: str = "default_session",
    ) -> tuple[Generator[str, None, None], list[str]]:
        session = self._get_or_create_session(session_id)
        response_stream = session.send_message_stream(question)

        def stream_text() -> Generator[str, None, None]:
            for chunk in response_stream:
                text = getattr(chunk, "text", None)
                if text:
                    yield text

        return stream_text(), [KNOWLEDGE_BASE_FILE.name]

    def ask(self, question: str, session_id: str = "default_session") -> dict:
        session = self._get_or_create_session(session_id)
        response = session.send_message(question)
        return {
            "question": question,
            "answer": getattr(response, "text", "") or "",
            "sources": [KNOWLEDGE_BASE_FILE.name],
        }
