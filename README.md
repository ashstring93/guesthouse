# 물레방아하우스 (Guesthouse Web + API)

물레방아하우스 소개 웹사이트, 예약/결제 흐름, 그리고 Gemini 기반 숙소 안내 챗봇을 함께 제공하는 프로젝트입니다.

## 주요 기능

- 숙소 소개/객실/위치/리뷰 페이지 제공
- 예약 현황 달력 조회 (`/reservation/list`)
- 예약/결제 준비 페이지 (`/reservation/book`)
- 예약 확인 조회 (`/reservation/check`)
- 토스페이먼츠 V2 결제 연동 (성공/실패/취소 처리, 가상계좌 미지원)
- 관리자 대시보드 (예약 목록, 결제 취소, 예약 차단일 관리)
- Gemini 2.5 Flash-Lite 기반 SSE 스트리밍 챗봇 (`/api/chat`)
- SQLite 기반 예약/약관동의/챗로그 저장

## 디렉토리 구조

```text
.
├─ backend/
│  ├─ server.py               # 메인 앱 (FastAPI 생성, 라우터 등록)
│  ├─ config.py               # 환경변수, 상수, 경로 설정
│  ├─ database.py             # DB 초기화, 커넥션, 저장/조회
│  ├─ models.py               # Pydantic 요청 모델
│  ├─ utils.py                # 날짜 파싱, 요금 계산, 환불, 토스 인증
│  ├─ chatbot.py              # Gemini 기반 RAG 챗봇
│  ├─ routes/
│  │  ├─ pages.py             # HTML 페이지 서빙, favicon, 헬스체크
│  │  ├─ payment.py           # 결제 API (견적, 준비, 성공/실패 콜백)
│  │  ├─ reservation.py       # 캘린더 설정, 마감일, 예약 조회
│  │  ├─ admin.py             # 관리자 API (예약 목록, 결제 취소)
│  │  └─ chat.py              # 챗봇 스트리밍 응답
│  ├─ knowledge_base/
│  │  └─ integrated_accommodation_guide.md  # 챗봇 RAG용 숙소 안내 문서
│  ├─ .env                    # 환경변수 (Git 제외)
│  └─ .env.example            # 환경변수 템플릿
│
├─ frontend/
│  ├─ index.html              # 메인 페이지
│  ├─ css/
│  │  ├─ style.css            # 공통 레이아웃, 헤더, 네비게이션
│  │  ├─ about.css            # 숙소 소개 섹션
│  │  ├─ rooms.css            # 객실 소개 섹션
│  │  ├─ reviews.css          # 리뷰 섹션
│  │  ├─ chatbot.css          # 챗봇 위젯
│  │  ├─ payment.css          # 예약/결제 페이지
│  │  ├─ reservation.css      # 예약 캘린더/확인 페이지
│  │  ├─ reservation-hub.css  # 예약 현황 페이지
│  │  ├─ footer.css           # 푸터
│  │  └─ responsive.css       # 반응형 미디어쿼리
│  ├─ js/
│  │  ├─ script.js            # 메인 페이지 (네이버 지도, 슬라이더)
│  │  ├─ chatbot.js           # 챗봇 위젯 로직
│  │  ├─ payment.js           # 예약/결제 로직 (토스 위젯 연동)
│  │  ├─ reservation-calendar.js  # 예약 캘린더 컴포넌트
│  │  ├─ reservation-check.js     # 예약 조회 로직
│  │  └─ reservation-list.js      # 예약 현황 초기화
│  ├─ images/                 # 압축된 숙소 사진, 로고, OG 이미지
│  ├─ fonts/                  # 커스텀 폰트 (학교안심우주)
│  └─ pages/
│     ├─ reservation/
│     │  ├─ book.html         # 예약/결제 페이지
│     │  ├─ list.html         # 예약 현황 캘린더
│     │  └─ check.html        # 예약 확인 페이지
│     └─ admin/
│        └─ admin-dashboard.html  # 관리자 대시보드
│
├─ docs/archive/              # 아카이브 문서
├─ requirements.txt           # Python 의존성
└─ README.md
```

## 빠른 시작

### 1) 가상환경 생성 및 의존성 설치

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
```

### 2) 환경변수 설정

`backend/.env.example`을 참고해 `backend/.env` 파일을 생성하고 값을 채웁니다.

필수:

- `GEMINI_API_KEY`

### 3) 서버 실행

```bash
cd backend
python server.py
```

기본 실행 주소:

- 앱: `http://localhost:8000`
- API 문서: `http://localhost:8000/docs`

## 환경변수 요약

`backend/.env` 기준:

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `GEMINI_API_KEY` | Gemini API 키 **(필수)** | - |
| `GEMINI_MODEL` | 사용할 Gemini 모델 | `gemini-2.5-flash-lite` |
| `PORT` | 서버 포트 | `8000` |
| `UVICORN_RELOAD` | 개발 중 자동 재시작 여부 (`true`/`false`) | `false` |
| `CORS_ORIGINS` | 허용할 오리진 목록 (쉼표 구분) | `http://localhost:8000` |
| `BASE_WEEKDAY_RATE` | 평일 1박 요금 | `184847` |
| `BASE_WEEKEND_RATE` | 주말 1박 요금 | `242612` |
| `BASE_GUESTS` / `MAX_GUESTS` | 기본/최대 인원 | `2` / `8` |
| `ADULT_EXTRA_FEE` | 추가 인원 요금 (1인/1박) | `20000` |
| `BBQ_FEE` | BBQ 옵션 요금 | `20000` |
| `TOSSPAYMENTS_WIDGET_CLIENT_KEY` | 토스 위젯 클라이언트 키 | - |
| `TOSSPAYMENTS_PAYMENT_METHOD_VARIANT_KEY` | 가상계좌를 제거한 토스 결제 UI variantKey | `DEFAULT` |
| `TOSSPAYMENTS_SECRET_KEY` | 토스 시크릿 키 | - |
| `TOSSPAYMENTS_API_BASE` | 토스 API 기본 주소 | `https://api.tosspayments.com` |
| `PAYMENT_TERMS_VERSION` | 결제 약관 스냅샷 버전 | `2026-03-09-v1` |
| `BOOKED_STATUSES` | 예약 마감으로 처리할 결제 상태 목록 | `confirming,confirmed,paid` |
| `HOLIDAY_DATES` | 수동 공휴일 목록 (쉼표 구분, `YYYY-MM-DD`) | - |
| `ADMIN_DASHBOARD_TOKEN` | 관리자 대시보드 인증 토큰 | - |

토스 결제 UI는 상점관리자에서 가상계좌를 제거한 variantKey를 사용하는 것을 전제로 합니다. 서버에서도 결제 승인 후 가상계좌 결제수단이 확인되면 자동 취소하고 예약을 확정하지 않습니다.

## 주요 API

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/health` | 서버 헬스체크 |
| `GET` | `/api/calendar/config` | 달력 요금/공휴일 설정 |
| `GET` | `/api/calendar/availability` | 예약 마감일 목록 |
| `POST` | `/api/payment/quote` | 요금 견적 |
| `GET` | `/api/payment/config` | 토스 클라이언트 키 |
| `POST` | `/api/payment/prepare` | 주문 생성/결제 준비 |
| `GET` | `/reservation/success` | 토스 결제 성공 콜백 |
| `GET` | `/reservation/fail` | 토스 결제 실패 콜백 |
| `POST` | `/api/reservation/check` | 이름+연락처로 예약 조회 |
| `GET` | `/api/admin/date-blocks` | 관리자 예약 차단일 목록 |
| `POST` | `/api/admin/date-blocks` | 관리자 예약 차단일 추가 |
| `DELETE` | `/api/admin/date-blocks/{block_id}` | 관리자 예약 차단일 삭제 |
| `GET` | `/api/admin/reservations` | 관리자 예약 목록 |
| `POST` | `/api/admin/cancel-payment` | 관리자 결제 취소 |
| `POST` | `/api/chat` | 챗봇 SSE 스트리밍 응답 (`text/event-stream`) |

## 데이터 저장

로컬 SQLite 파일: `backend/guesthouse.db`

| 테이블 | 용도 |
|--------|------|
| `chat_logs` | 챗봇 대화 기록 |
| `payment_intents` | 예약/결제 정보 |
| `payment_term_consents` | 약관 동의 기록 |
| `admin_date_blocks` | 관리자 예약 차단일 |

## 이미지 관리

실제 페이지는 `frontend/images/`의 압축 이미지 파일을 사용합니다.

- 메인 히어로: `hero-*.jpg`
- 객실 갤러리: `gallery-*.jpg`
- 소개/미리보기: `about-garden-view.jpg`, `og-cover.jpg`

원본 사진 폴더 `frontend/images/new_images/`는 로컬 작업용이며 Git에 포함하지 않습니다. 원본을 교체할 때는 압축본을 다시 생성한 뒤 HTML에서 압축 파일만 참조합니다.
