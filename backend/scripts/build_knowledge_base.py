"""
물레방아하우스 지식 베이스 구축 스크립트 (Updated)

새로운 google.genai SDK를 사용하여 벡터 DB 구축
"""

import os
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from google import genai
from google.genai import types
import numpy as np

# 환경 변수 로드
load_dotenv()

# 설정
KNOWLEDGE_BASE_DIR = "./knowledge_base"
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


class GeminiEmbeddings:
    """새로운 google.genai SDK를 위한 LangChain 호환 래퍼"""

    def __init__(self, api_key: str, model: str = "gemini-embedding-001"):
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """여러 문서를 임베딩"""
        embeddings = []
        for text in texts:
            result = self.client.models.embed_content(model=self.model, contents=text)
            embeddings.append(result.embeddings[0].values)
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        """단일 쿼리를 임베딩"""
        result = self.client.models.embed_content(model=self.model, contents=text)
        return result.embeddings[0].values


def build_knowledge_base():
    """지식 베이스를 구축하고 벡터 DB에 저장"""

    print("📚 지식 베이스 구축 시작...")

    # 1. 문서 로딩
    print(f"📄 {KNOWLEDGE_BASE_DIR}에서 문서 로딩 중...")
    loader = DirectoryLoader(KNOWLEDGE_BASE_DIR, glob="**/*.md", show_progress=True)
    documents = loader.load()
    print(f"✅ {len(documents)}개의 문서 로드 완료")

    # 2. 텍스트 분할
    print("✂️  문서를 청크로 분할 중...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,  # 한 청크당 약 800자
        chunk_overlap=100,  # 100자 오버랩으로 컨텍스트 유지
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = text_splitter.split_documents(documents)
    print(f"✅ {len(chunks)}개의 청크 생성 완료")

    # 3. 임베딩 생성 및 벡터 스토어 구축
    print("🔮 Gemini 임베딩 생성 및 ChromaDB 저장 중...")
    embeddings = GeminiEmbeddings(api_key=GEMINI_API_KEY)

    # ChromaDB에 저장
    vectorstore = Chroma.from_documents(
        documents=chunks, embedding=embeddings, persist_directory=CHROMA_PERSIST_DIR
    )

    print(f"✅ 벡터 DB가 {CHROMA_PERSIST_DIR}에 저장되었습니다.")

    # 4. 테스트 검색
    print("\n🔍 테스트 검색 수행 중...")
    test_queries = [
        "체크인 시간이 언제인가요?",
        "반려동물 동반이 가능한가요?",
        "주차가 가능한가요?",
    ]

    for query in test_queries:
        results = vectorstore.similarity_search(query, k=1)
        print(f"\n질문: {query}")
        if results:
            print(f"  ✅ 관련 문서 발견:")
            print(f"     출처: {results[0].metadata.get('source', 'Unknown')}")
            print(f"     내용: {results[0].page_content[:150]}...")

    print("\n✨ 지식 베이스 구축 완료!")

    return vectorstore


if __name__ == "__main__":
    try:
        vectorstore = build_knowledge_base()
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback

        traceback.print_exc()
