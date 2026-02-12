# Backend README

## 설치 방법

1. 가상환경 생성 (권장):
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

2. 의존성 설치:
```bash
pip install -r requirements.txt
```

3. 환경 변수 설정:
- `.env.example`을 복사하여 `.env` 파일 생성
- `GEMINI_API_KEY`에 본인의 API 키 입력

4. 서버 실행:
```bash
uvicorn app:app --reload --port 8001
```

## API 엔드포인트

- `POST /api/chat` - 챗봇 대화
- `GET /api/health` - 헬스체크
