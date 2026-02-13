# 물레방아하우스 AI 챗봇 사용자 가이드

## 🎯 개요

물레방아하우스 웹사이트에 통합된 AI 챗봇으로, 게스트님들의 궁금하신 사항에 24시간 자동으로 답변합니다.

## 🚀 시작하기

### 1. 백엔드 서버 실행

```bash
cd backend
python server.py
```

서버가 http://localhost:8000 에서 실행됩니다.

### 2. 웹사이트 접속

백엔드 서버가 프론트 파일도 함께 서빙하므로 아래 주소로 접속하면 됩니다.

```bash
http://localhost:8000
```

## 💬 챗봇 사용 방법

### 웹사이트에서 챗봇 열기

1. 웹사이트 우측 하단의 **보라색 플로팅 버튼** 클릭
2. 챗봇 대화창이 나타납니다
3. 환영 메시지와 함께 추천 질문이 표시됩니다

### 질문하기

**방법 1**: 추천 질문 클릭
- 체크인 시간이 언제인가요?
- 반려동물을 데리고 갈 수 있나요?
- 한옥마을까지 얼마나 걸리나요?

**방법 2**: 직접 입력
1. 하단 입력창에 질문 입력
2. 전송 버튼 클릭 또는 Enter 키

### AI 응답

- AI가 지식 베이스에서 관련 정보를 검색합니다
- 자연스러운 한국어로 답변을 생성합니다
- 참고한 문서 출처를 함께 표시합니다

## 📚 주요 기능

### 1. 플로팅 챗봇 버튼
- 우측 하단 고정
- 보라색 그라데이션 디자인
- 호버 효과 (확대 + 그림자)

### 2. 대화 인터페이스
- 깔끔한 메시지 버블 (사용자: 우측, AI: 좌측)
- 타이핑 인디케이터 (AI가 답변을 생성 중일 때)
- 스크롤 가능한 메시지 영역
- 참고 문서 출처 표시

### 3. 반응형 디자인
- 데스크톱: 우측 하단 플로팅 창
- 모바일: 전체 화면 모드

## 🔧 기술 스택

### 백엔드
- **FastAPI**: REST API 서버
- **LangChain**: RAG 파이프라인
- **ChromaDB**: 벡터 데이터베이스
- **Gemini 2.5 Flash-Lite**: LLM 모델

### 프론트엔드
- **Vanilla JavaScript**: 챗봇 로직
- **CSS3**: 애니메이션 및 스타일
- **Fetch API**: 백엔드 통신

## 📁 파일 구조

```
물레방아하우스/
├── backend/
│   ├── server.py                 # FastAPI 서버
│   ├── chatbot.py                # RAG 챗봇 클래스
│   ├── knowledge_base/           # 지식 베이스 (6개 MD 파일)
│   └── chroma_db/                # 벡터 DB
├── frontend/
│   ├── index.html                # 메인 웹페이지
│   ├── css/
│   │   └── chatbot.css           # 챗봇 스타일
│   └── js/
│       └── chatbot.js            # 챗봇 JavaScript
└── review.txt                    # 리뷰 원본 텍스트
```

## 🌐 API 엔드포인트

### POST /api/chat
챗봇 대화 엔드포인트

**요청**:
```json
{
  "question": "체크인 시간이 언제인가요?"
}
```

**응답**:
```json
{
  "question": "체크인 시간이 언제인가요?",
  "answer": "체크인은 오후 3시(15:00)부터 가능합니다...",
  "sources": ["checkin_checkout.md", "faq.md"]
}
```

### GET /api/health
서버 상태 확인

**응답**:
```json
{
  "status": "healthy",
  "chatbot_loaded": true
}
```

## ⚙️ 커스터마이징

### 챗봇 스타일 변경

`frontend/css/chatbot.css`에서 색상, 크기, 애니메이션 등을 수정할 수 있습니다:

```css
/* 플로팅 버튼 색상 변경 */
.chatbot-button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

/* 챗봇 위치 변경 */
.chatbot-button {
    bottom: 30px;  /* 하단 여백 */
    right: 30px;   /* 우측 여백 */
}
```

### API URL 변경

기본값은 상대 경로(`/api/chat`)이며, 필요하면 `apiUrl`을 넘겨서 외부 백엔드를 지정할 수 있습니다:

```javascript
window.chatbot = new MullebangChatbot('https://your-backend-url.com');
```

## 🐛 문제 해결

### 챗봇이 응답하지 않아요
1. 백엔드 서버가 실행 중인지 확인
2. 브라우저 콘솔에서 오류 확인 (F12)
3. `/api/health` 엔드포인트 테스트

### CORS 오류가 발생해요
백엔드 `server.py`에서 CORS 설정 확인:
```python
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8000").split(",")
```

### 챗봇 버튼이 보이지 않아요
1. `frontend/css/chatbot.css`가 올바르게 로드되었는지 확인
2. `frontend/js/chatbot.js`가 올바르게 로드되었는지 확인
3. 브라우저 개발자 도구에서 요소 검사

## 🔐 보안 고려사항

- API 키는 `.env` 파일에 저장 (Git에 커밋하지 않음)
- 개인정보는 지식 베이스에 포함하지 않음
- HTTPS 사용 권장 (프로덕션 환경)

## 📞 지원

문의사항이 있으시면 호스트에게 연락해주세요:
- 전화: 010-9243-8495

---

**©2024 물레방아하우스 - AI 챗봇 powered by Gemini 2.5 Flash-Lite**
