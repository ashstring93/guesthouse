"""Build and validate the guesthouse knowledge-base vector DB."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

BACKEND_DIR = Path(__file__).resolve().parents[1]


def resolve_backend_path(raw_path: str | None, default_path: Path) -> Path:
    """Resolve relative paths against backend dir for stable behavior."""
    if not raw_path:
        return default_path

    path = Path(raw_path)
    if path.is_absolute():
        return path
    return BACKEND_DIR / path


KNOWLEDGE_BASE_DIR = BACKEND_DIR / "knowledge_base"
CHROMA_PERSIST_DIR = resolve_backend_path(
    os.getenv("CHROMA_PERSIST_DIRECTORY"), BACKEND_DIR / "chroma_db"
)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def safe_print(message: str):
    """Print text safely for non-UTF8 Windows consoles."""
    encoding = sys.stdout.encoding or "utf-8"
    output = message.encode(encoding, errors="replace").decode(encoding)
    print(output)


class GeminiEmbeddings:
    """LangChain-compatible wrapper for google.genai embeddings."""

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


def build_knowledge_base():
    """Build knowledge base and persist ChromaDB."""
    safe_print("[INFO] Start building knowledge base")

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set.")

    safe_print(f"[INFO] Loading markdown files from: {KNOWLEDGE_BASE_DIR}")
    loader = DirectoryLoader(str(KNOWLEDGE_BASE_DIR), glob="**/*.md", show_progress=True)
    documents = loader.load()
    safe_print(f"[OK] Loaded documents: {len(documents)}")

    safe_print("[INFO] Splitting documents into chunks")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = text_splitter.split_documents(documents)
    safe_print(f"[OK] Created chunks: {len(chunks)}")

    safe_print(f"[INFO] Building ChromaDB at: {CHROMA_PERSIST_DIR}")
    embeddings = GeminiEmbeddings(api_key=GEMINI_API_KEY)
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_PERSIST_DIR),
    )
    safe_print("[OK] ChromaDB persisted")

    safe_print("[INFO] Running quick retrieval checks")
    test_queries = [
        "체크인 시간이 언제인가요?",
        "반려동물 동반이 가능한가요?",
        "주차가 가능한가요?",
    ]

    for query in test_queries:
        results = vectorstore.similarity_search(query, k=1)
        safe_print(f"[QUERY] {query}")
        if results:
            source = results[0].metadata.get("source", "Unknown")
            snippet = results[0].page_content[:150].replace("\n", " ")
            safe_print(f"[HIT] source={source}")
            safe_print(f"[HIT] snippet={snippet}...")
        else:
            safe_print("[HIT] no result")

    safe_print("[DONE] Knowledge base build complete")
    return vectorstore


if __name__ == "__main__":
    try:
        build_knowledge_base()
    except Exception as e:
        safe_print(f"[ERROR] {e}")
        import traceback

        traceback.print_exc()
