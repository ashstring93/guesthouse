# Backend README

## 운영 절차

1. 가상환경 생성 (권장)
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

2. 의존성 설치
```bash
pip install -r requirements.txt
```

3. 환경 변수 설정
- `.env.example`을 복사해서 `.env` 파일 생성
- `GEMINI_API_KEY` 값 입력

4. 지식베이스 문서 업데이트 (필요 시)
- `backend/knowledge_base/*.md` 수정

5. 벡터 DB 재생성
```bash
python scripts/build_knowledge_base.py
```

6. 서버 실행
```bash
python server.py
```

기본 주소: `http://localhost:8000`
- 프런트 정적 파일 위치: `frontend/` (`index.html`, `css/`, `js/`, `images/`)

## API 엔드포인트

- `POST /api/chat` - 챗봇 대화
- `GET /api/health` - 헬스체크

## 수동 점검

표준 점검 스크립트:
```bash
python quick_test.py
```

또는 API 직접 점검:

```bash
curl http://localhost:8000/api/health
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"체크인 시간이 언제인가요?\"}"
```
