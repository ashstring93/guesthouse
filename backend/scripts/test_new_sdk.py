"""
새로운 google.genai SDK로 임베딩 테스트
"""

import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print("=" * 60)
print("🔑 새로운 Gemini SDK 임베딩 테스트")
print("=" * 60)

try:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    print("\n✅ google.genai SDK import 성공")

    # 임베딩 테스트
    print("\n📝 임베딩 테스트 중...")
    text = "물레방아하우스는 전주 한옥마을 근처에 위치한 게스트하우스입니다."

    result = client.models.embed_content(model="gemini-embedding-001", contents=text)

    print(f"✅ 임베딩 성공!")
    print(f"   텍스트: {text}")
    print(f"   벡터 차원: {len(result.embeddings[0].values)}")
    print(f"   첫 5개 값: {result.embeddings[0].values[:5]}")

except ImportError as e:
    print(f"❌ Import 에러: {e}")
    print("\n💡 해결방법: pip install google-genai")

except Exception as e:
    print(f"❌ 임베딩 실패: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 60)
