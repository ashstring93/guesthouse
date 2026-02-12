"""
현재 Gemini API 키의 권한을 테스트하는 스크립트
"""

import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print("=" * 60)
print("🔑 Gemini API 키 권한 테스트")
print("=" * 60)
print(f"\nAPI Key: {api_key[:20]}...{api_key[-4:]}\n")

# 테스트 1: google.generativeai 패키지로 임베딩 테스트
print("📝 테스트 1: google.generativeai 패키지")
print("-" * 60)
try:
    import google.generativeai as genai

    genai.configure(api_key=api_key)

    # embedding-001 테스트
    try:
        result = genai.embed_content(
            model="models/embedding-001", content="테스트 문장"
        )
        print("✅ models/embedding-001: 사용 가능")
        print(f"   벡터 차원: {len(result['embedding'])}")
    except Exception as e:
        print(f"❌ models/embedding-001: 실패")
        print(f"   오류: {str(e)[:100]}")

    # text-embedding-004 테스트
    try:
        result = genai.embed_content(
            model="models/text-embedding-004", content="테스트 문장"
        )
        print("✅ models/text-embedding-004: 사용 가능")
        print(f"   벡터 차원: {len(result['embedding'])}")
    except Exception as e:
        print(f"❌ models/text-embedding-004: 실패")
        print(f"   오류: {str(e)[:100]}")

except Exception as e:
    print(f"❌ 패키지 오류: {e}")

# 테스트 2: LangChain 패키지로 임베딩 테스트
print("\n📝 테스트 2: LangChain 패키지")
print("-" * 60)
try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    # embedding-001
    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001", google_api_key=api_key
        )
        result = embeddings.embed_query("테스트")
        print("✅ LangChain embedding-001: 사용 가능")
        print(f"   벡터 차원: {len(result)}")
    except Exception as e:
        print(f"❌ LangChain embedding-001: 실패")
        print(f"   오류: {str(e)[:100]}")

    # text-embedding-004
    try:
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004", google_api_key=api_key
        )
        result = embeddings.embed_query("테스트")
        print("✅ LangChain text-embedding-004: 사용 가능")
        print(f"   벡터 차원: {len(result)}")
    except Exception as e:
        print(f"❌ LangChain text-embedding-004: 실패")
        print(f"   오류: {str(e)[:100]}")

except Exception as e:
    print(f"❌ 패키지 오류: {e}")

# 테스트 3: 채팅 모델 테스트 (비교용)
print("\n📝 테스트 3: 채팅 모델 (비교용)")
print("-" * 60)
try:
    import google.generativeai as genai

    genai.configure(api_key=api_key)

    model = genai.GenerativeModel("gemini-2.0-flash-lite")
    response = model.generate_content("Hi")
    print("✅ gemini-2.0-flash-lite: 사용 가능")
    print(f"   응답: {response.text[:50]}...")
except Exception as e:
    print(f"❌ 채팅 모델 실패: {str(e)[:100]}")

print("\n" + "=" * 60)
print("✨ 테스트 완료!")
print("=" * 60)
