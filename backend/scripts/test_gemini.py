"""
Gemini API 연결 테스트
"""

import os
from dotenv import load_dotenv
from google import generativeai as genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key loaded: {api_key[:20]}...")

# Gemini 설정
genai.configure(api_key=api_key)

# 모델 목록 확인
print("\n사용 가능한 모델 목록:")
for model in genai.list_models():
    if "generateContent" in model.supported_generation_methods:
        print(f"  - {model.name}")

# 임베딩 모델 테스트
print("\n임베딩 모델 테스트:")
try:
    result = genai.embed_content(
        model="models/embedding-001", content="테스트 문장입니다"
    )
    print(f"✅ 임베딩 성공! 벡터 차원: {len(result['embedding'])}")
except Exception as e:
    print(f"❌ 임베딩 실패: {e}")

# 채팅 모델 테스트
print("\n채팅 모델 테스트:")
try:
    model = genai.GenerativeModel("gemini-2.0-flash-lite")
    response = model.generate_content("안녕하세요!")
    print(f"✅ 채팅 성공! 응답: {response.text[:100]}")
except Exception as e:
    print(f"❌ 채팅 실패: {e}")
