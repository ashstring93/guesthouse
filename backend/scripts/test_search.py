"""
벡터 DB 검색 기능 테스트
"""

import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from google import genai

load_dotenv()


class GeminiEmbeddings:
    """google.genai SDK를 위한 LangChain 호환 래퍼"""

    def __init__(self, api_key: str, model: str = "gemini-embedding-001"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = []
        for text in texts:
            result = self.client.models.embed_content(model=self.model, contents=text)
            embeddings.append(result.embeddings[0].values)
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        result = self.client.models.embed_content(model=self.model, contents=text)
        return result.embeddings[0].values


print("=" * 70)
print("🔍 벡터 DB 검색 테스트")
print("=" * 70)

# 벡터 DB 로드
embeddings = GeminiEmbeddings(api_key=os.getenv("GEMINI_API_KEY"))
vectorstore = Chroma(persist_directory="./chroma_db", embedding_function=embeddings)

# 테스트 질문들
test_questions = [
    "체크인 시간이 언제인가요?",
    "반려동물을 데리고 갈 수 있나요?",
    "한옥마을까지 얼마나 걸리나요?",
    "주차가 가능한가요?",
    "바비큐를 할 수 있나요?",
    "숙박 요금이 얼마인가요?",
]

for question in test_questions:
    print(f"\n질문: {question}")
    print("-" * 70)

    # 관련 문서 검색 (상위 2개)
    results = vectorstore.similarity_search(question, k=2)

    for i, doc in enumerate(results, 1):
        source = doc.metadata.get("source", "Unknown").split("\\")[-1]
        content = doc.page_content.replace("\n", " ").strip()
        print(f"\n  [{i}] 출처: {source}")
        print(f"      내용: {content[:200]}...")

print("\n" + "=" * 70)
print("✅ 검색 테스트 완료!")
print("=" * 70)
