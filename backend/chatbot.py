import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from google import genai
from typing import Optional, List, Any

BACKEND_DIR = Path(__file__).resolve().parent


def resolve_chroma_persist_dir(raw_path: Optional[str] = None) -> Path:
    """Resolve Chroma path relative to backend dir when env uses relative path."""
    if raw_path is None:
        raw_path = os.getenv("CHROMA_PERSIST_DIRECTORY")

    if not raw_path:
        return BACKEND_DIR / "chroma_db"

    path = Path(raw_path)
    if path.is_absolute():
        return path
    return BACKEND_DIR / path


class GeminiEmbeddings:
    """google.genai SDK를 위한 LangChain 호환 임베딩 래퍼"""

    def __init__(self, api_key: str, model: str = "gemini-embedding-001"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            result = self.client.models.embed_content(model=self.model, contents=text)
            embeddings.append(result.embeddings[0].values)
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        result = self.client.models.embed_content(model=self.model, contents=text)
        return result.embeddings[0].values


class GuestHouseChatbot:
    """물레방아하우스 챗봇"""

    def __init__(self, api_key: str, chroma_persist_directory: Optional[str] = None):
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.chroma_persist_dir = resolve_chroma_persist_dir(chroma_persist_directory)

        # 임베딩 모델
        self.embeddings = GeminiEmbeddings(api_key=api_key)

        # 벡터 DB 로드
        self.vectorstore = Chroma(
            persist_directory=str(self.chroma_persist_dir),
            embedding_function=self.embeddings,
        )

        # Retriever 설정
        self.retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": 3}  # 상위 3개 관련 문서 검색
        )

    def generate_answer(self, question: str, context: str) -> str:
        """Gemini를 사용하여 답변 생성"""
        prompt = f"""당신은 물레방아하우스 게스트하우스의 친절한 안내 봇입니다.
아래 제공된 정보를 바탕으로 게스트의 질문에 정확하고 친절하게 답변해주세요.

제공된 정보:
{context}

게스트 질문: {question}

답변 가이드라인:
1. 친절하고 따뜻한 말투를 사용하세요
2. 제공된 정보에 기반하여 정확하게 답변하세요
3. 정보가 불충분하면 솔직하게 말하고, 호스트(010-9243-8495)에게 문의하도록 안내하세요
4. 가격, 시간 등 구체적인 정보는 정확히 전달하세요
5. 자연스러운 대화체를 사용하세요

답변:"""

        response = self.client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config={
                "temperature": 0.7,
                "max_output_tokens": 1024,
            },
        )
        return response.text

    def ask(self, question: str) -> dict:
        """질문에 답변"""
        # 관련 문서 검색
        docs = self.retriever.invoke(question)

        # 컨텍스트 생성
        context = "\n\n".join([doc.page_content for doc in docs])

        # 답변 생성
        answer = self.generate_answer(question, context)

        return {
            "question": question,
            "answer": answer,
            "sources": [
                doc.metadata.get("source", "Unknown").split("\\")[-1]
                for doc in docs
            ],
        }


def main():
    """챗봇 테스트"""
    # Load env files if present. backend/.env overrides root .env.
    load_dotenv(BACKEND_DIR.parent / ".env")
    load_dotenv(BACKEND_DIR / ".env", override=True)

    print("=" * 70)
    print("🏠 물레방아하우스 AI 챗봇 테스트")
    print("=" * 70)

    # 챗봇 초기화
    api_key = os.getenv("GEMINI_API_KEY")
    chatbot = GuestHouseChatbot(api_key=api_key)

    print("\n✅ 챗봇 초기화 완료!")
    print(f"   모델: gemini-2.5-flash-lite")
    print(f"   벡터 DB: ChromaDB")
    print(f"   검색 범위: 상위 3개 관련 문서\n")

    # 테스트 질문들
    test_questions = [
        "체크인 시간이 언제인가요?",
        "반려동물을 데리고 갈 수 있나요?",
        "숙박 요금이 얼마인가요?",
        "한옥마을까지 어떻게 가나요?",
    ]

    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*70}")
        print(f"질문 {i}: {question}")
        print(f"{'-'*70}")

        result = chatbot.ask(question)

        print(f"답변:\n{result['answer']}")
        print(f"\n📚 참고 문서: {', '.join(result['sources'])}")

    print(f"\n{'='*70}")
    print("✨ 테스트 완료!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
