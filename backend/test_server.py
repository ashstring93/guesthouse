"""
FastAPI 서버 테스트 스크립트
"""

import requests
import json

BASE_URL = "http://localhost:8000"


def test_health():
    """헬스 체크 테스트"""
    print("=" * 70)
    print("🏥 Health Check 테스트")
    print("=" * 70)

    response = requests.get(f"{BASE_URL}/api/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}\n")


def test_chat(question: str):
    """챗봇 테스트"""
    print(f"\n{'='*70}")
    print(f"질문: {question}")
    print(f"{'-'*70}")

    response = requests.post(f"{BASE_URL}/api/chat", json={"question": question})

    if response.status_code == 200:
        result = response.json()
        print(f"답변:\n{result['answer']}")
        print(f"\n📚 참고 문서: {', '.join(result['sources'])}")
    else:
        print(f"❌ 오류: {response.status_code}")
        print(f"   {response.text}")


def main():
    """메인 테스트 실행"""
    print("\n🧪 FastAPI 서버 테스트 시작\n")

    # 1. Health Check
    test_health()

    # 2. 챗봇 질문 테스트
    test_questions = [
        "체크인 시간이 언제인가요?",
        "반려동물을 데리고 가도 되나요?",
        "주차 공간이 있나요?",
        "가격이 얼마인가요?",
    ]

    for question in test_questions:
        test_chat(question)

    print(f"\n{'='*70}")
    print("✅ 테스트 완료!")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
