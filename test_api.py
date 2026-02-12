import requests

print("🧪 백엔드 API 테스트\n")

# 1. Health Check
print("1. Health Check 테스트...")
try:
    response = requests.get("http://localhost:8000/api/health")
    print(f"   상태 코드: {response.status_code}")
    print(f"   응답: {response.json()}")
except Exception as e:
    print(f"   ❌ 오류: {e}")

print()

# 2. Chat API
print("2. Chat API 테스트...")
try:
    response = requests.post(
        "http://localhost:8000/api/chat", json={"question": "체크인 시간이 언제인가요?"}
    )
    print(f"   상태 코드: {response.status_code}")
    if response.ok:
        data = response.json()
        print(f"   질문: {data['question']}")
        print(f"   답변: {data['answer'][:100]}...")
        print(f"   소스: {data['sources']}")
    else:
        print(f"   ❌ 응답: {response.text}")
except Exception as e:
    print(f"   ❌ 오류: {e}")
