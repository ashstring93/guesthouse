"""간단한 API 테스트 - urllib 사용"""
import urllib.request
import json

# Health Check
print("=" * 70)
print("🏥 Health Check")
print("=" * 70)
try:
    with urllib.request.urlopen("http://localhost:8000/api/health") as response:
        data = json.loads(response.read().decode())
        print(f"✅ Status: {response.status}")
        print(f"   Response: {json.dumps(data, indent=2, ensure_ascii=False)}\n")
except Exception as e:
    print(f"❌ Error: {e}\n")

# Chat Test
print("=" * 70)
print("💬 Chat Test")
print("=" * 70)

question = "체크인 시간이 언제인가요?"
print(f"질문: {question}\n")

try:
    req_data = json.dumps({"question": question}).encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:8000/api/chat",
        data=req_data,
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode())
        print(f"답변:\n{data['answer']}\n")
        print(f"📚 참고: {', '.join(data['sources'])}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 70)
