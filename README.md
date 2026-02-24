# 물레방아하우스 (Guesthouse Web + API)

물레방아하우스 소개 웹사이트, 예약/결제 흐름, 그리고 Gemini 기반 숙소 안내 챗봇을 함께 제공하는 프로젝트입니다.

## 주요 기능

- 숙소 소개/객실/위치/리뷰 페이지 제공
- 예약 현황 달력 조회 (`/reservation/list`)
- 예약/결제 준비 페이지 (`/reservation/book`)
- 예약 확인 조회 (`/reservation/check`)
- Gemini 2.5 Flash-Lite 기반 스트리밍 챗봇 (`/api/chat`)
- SQLite 기반 예약/약관동의/챗로그 저장

## 디렉토리 구조

```text
.
├─ backend/
│  ├─ server.py
│  ├─ chatbot.py
│  ├─ .env.example
│  └─ knowledge_base/
├─ frontend/
│  ├─ index.html
│  ├─ css/
│  ├─ js/
│  ├─ images/
│  └─ pages/reservation/
└─ requirements.txt
```

## 빠른 시작

### 1) 의존성 설치

```bash
pip install -r requirements.txt
```

### 2) 환경변수 설정

`backend/.env.example`을 참고해 `backend/.env` 파일을 생성하고 값을 채웁니다.

필수:

- `GEMINI_API_KEY`

### 3) 서버 실행

프로젝트 루트에서:

```bash
cd backend
python server.py
```

기본 실행 주소:

- 앱: `http://localhost:8000`
- API 문서: `http://localhost:8000/docs`

## 환경변수 요약

`backend/.env` 기준:

- `GEMINI_API_KEY`: Gemini API 키 (필수)
- `PORT`: 서버 포트
- `CORS_ORIGINS`: 허용할 오리진 목록(콤마 구분)
- `HOLIDAY_DATES`: 추가 공휴일(YYYY-MM-DD, 콤마 구분)
- `BASE_WEEKDAY_RATE`, `BASE_WEEKEND_RATE`: 기본 숙박 요금
- `BASE_GUESTS`, `MAX_GUESTS`: 기본/최대 인원
- `ADULT_EXTRA_FEE`, `CHILD_EXTRA_FEE`, `INFANT_EXTRA_FEE`: 인원 추가 요금
- `BBQ_FEE`: 바베큐 옵션 요금
- `PAYMENT_CHECKOUT_URL`: 외부 결제 페이지 URL (없으면 주문 접수만 진행)
- `PAYMENT_TERMS_VERSION`, `BOOKED_STATUSES`: 결제/캘린더 정책 설정

## 주요 API

- `GET /api/health`: 서버 헬스체크
- `GET /api/calendar/config`: 달력 요금/공휴일 설정 조회
- `GET /api/calendar/availability`: 예약 마감일 목록 조회
- `POST /api/payment/quote`: 요금 견적
- `POST /api/payment/prepare`: 주문 생성/결제 준비
- `POST /api/reservation/check`: 이름+연락처로 예약 조회
- `POST /api/chat`: 챗봇 스트리밍 응답

## 데이터 저장

로컬 SQLite 파일:

- `backend/chatbot_logs.db`

주요 테이블:

- `chat_logs`
- `payment_intents`
- `payment_term_consents`

