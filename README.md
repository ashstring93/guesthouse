<div align="center">

# 물레방아하우스

조용한 독채 숙소를 위한 소개 웹사이트, 예약·결제 흐름, 관리자 기능,  
그리고 Gemini 기반 숙소 안내 챗봇을 하나의 저장소로 운영하는 프로젝트입니다.

</div>

---

## 프로젝트 개요

이 저장소는 **물레방아하우스 운영에 필요한 웹 애플리케이션 전체**를 담고 있습니다.

- 숙소 소개용 랜딩 페이지
- 예약 가능일 조회 및 예약 확인
- 토스페이먼츠 기반 결제 흐름
- 관리자용 예약 관리 기능
- 숙소 안내용 Gemini 챗봇
- Docker 기반 배포 구조

> 운영 관점에서는 “코드는 저장소에”, “실제 환경값과 데이터는 서버에” 두는 구조를 목표로 합니다.

## 한눈에 보기

| 항목 | 내용 |
|---|---|
| 백엔드 | FastAPI, Uvicorn |
| 프론트엔드 | HTML, CSS, JavaScript |
| 결제 | TossPayments V2 |
| AI | Gemini API |
| 데이터 저장 | SQLite |
| 배포 방식 | Docker Compose |
| 기본 포트 | `8000` |

## 주요 기능

| 영역 | 설명 |
|---|---|
| 숙소 소개 | 메인 페이지, 객실 안내, 위치, 리뷰 섹션 제공 |
| 예약 흐름 | 예약 견적, 예약 준비, 예약 조회 기능 제공 |
| 결제 처리 | 토스페이먼츠 결제 준비, 성공/실패/취소 흐름 처리 |
| 관리자 기능 | 예약 목록 조회, 결제 취소, 예약 차단일 관리 |
| 챗봇 | 숙소 안내 문서를 기반으로 한 SSE 스트리밍 응답 |
| 운영 구조 | Docker 볼륨으로 SQLite 데이터를 소스코드와 분리 |

---

## 디렉터리 구조

```text
.
├─ backend/
│  ├─ server.py
│  ├─ config.py
│  ├─ database.py
│  ├─ models.py
│  ├─ utils.py
│  ├─ chatbot.py
│  ├─ routes/
│  │  ├─ admin.py
│  │  ├─ chat.py
│  │  ├─ pages.py
│  │  ├─ payment.py
│  │  └─ reservation.py
│  ├─ knowledge_base/
│  │  └─ integrated_accommodation_guide.md
│  ├─ .env.example
│  └─ guesthouse.db
├─ frontend/
│  ├─ index.html
│  ├─ css/
│  ├─ js/
│  ├─ images/
│  ├─ fonts/
│  └─ pages/
├─ data/
├─ docs/
├─ Dockerfile
├─ compose.yml
├─ .dockerignore
├─ requirements.txt
└─ README.md
```

## 구성 설명

| 경로 | 역할 |
|---|---|
| `backend/` | FastAPI 앱, 예약 로직, 결제 처리, 관리자 기능 |
| `backend/knowledge_base/` | 챗봇이 참고하는 숙소 안내 문서 |
| `frontend/` | 실제 사용자에게 보이는 정적 페이지 자산 |
| `data/` | Docker 실행 시 SQLite 파일을 보관하는 영속 볼륨 경로 |
| `docs/` | 아카이브 및 참고 문서 |
| `Caddyfile` | Caddy reverse proxy 설정 |

---

## 권장 실행 방식

이 프로젝트는 **Docker Compose 기준 운영**을 권장합니다.  
이 방식은 코드와 운영 데이터를 분리하기 쉽고, mini PC 같은 단일 서버 환경에서도 재현성이 좋습니다.

### 1. 환경변수 파일 생성

`backend/.env.example`을 복사해 `backend/.env`를 만듭니다.

```bash
cp backend/.env.example backend/.env
```

Windows PowerShell:

```powershell
Copy-Item backend/.env.example backend/.env
```

최소한 아래 값은 채워야 합니다.

- `GEMINI_API_KEY`
- `TOSSPAYMENTS_WIDGET_CLIENT_KEY`
- `TOSSPAYMENTS_SECRET_KEY`
- `ADMIN_DASHBOARD_TOKEN`

### 2. Docker로 실행

```bash
docker compose up -d --build
```

실행 후 접근 주소:

- 앱: `http://localhost`
- 헬스체크: `http://localhost/api/health`
- API 문서: `http://localhost/docs`

### 3. 종료

```bash
docker compose down
```

---

## Docker 운영 구조

컨테이너는 애플리케이션 코드를 실행하고, 실제 데이터는 별도 볼륨에 저장합니다.  
외부 요청은 Caddy가 받고, 내부적으로 FastAPI 컨테이너로 프록시합니다.

| 구분 | 경로 |
|---|---|
| 호스트 데이터 경로 | `./data` |
| 컨테이너 내부 데이터 경로 | `/data` |
| Docker 환경의 SQLite 경로 | `/data/guesthouse.db` |
| 외부 공개 포트 | `80`, `443` |
| 애플리케이션 내부 포트 | `8000` |

이 구조의 장점:

- 이미지를 다시 빌드해도 데이터가 유지됩니다.
- mini PC 초기화 이후에도 `data/`만 백업·복원하면 운영 복구가 쉬워집니다.
- 소스코드와 런타임 데이터를 명확히 분리할 수 있습니다.
- Caddy가 앞단에서 도메인 연결과 HTTPS 종료를 담당할 수 있습니다.

## Caddy 운영 메모

현재 `Caddyfile`은 로컬 확인용으로 `:80`에 바인딩되어 있습니다.

```caddy
:80 {
    encode zstd gzip
    reverse_proxy guesthouse:8000
}
```

외부 공개 시에는 첫 줄을 실제 도메인으로 바꾸면 됩니다.

```caddy
guesthouse.example.com {
    encode zstd gzip
    reverse_proxy guesthouse:8000
}
```

이후 아래 조건이 맞으면 Caddy가 HTTPS를 자동으로 처리합니다.

- 도메인 DNS가 mini PC의 공인 IP를 가리킴
- 공유기에서 `80`, `443` 포트를 mini PC로 포워딩함
- mini PC에서 Caddy가 `80`, `443` 포트를 점유 중임

## 로컬 개발 방식

Docker 없이 로컬에서 직접 실행할 수도 있습니다.

### 1. 가상환경 생성

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

macOS / Linux:

```bash
source venv/bin/activate
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경변수 파일 준비

`backend/.env.example`을 참고해 `backend/.env`를 생성합니다.

### 4. 실행

```bash
cd backend
python server.py
```

---

## 환경변수

`backend/.env` 파일을 기준으로 동작합니다.

| 변수명 | 설명 | 기본값 |
|---|---|---|
| `GEMINI_API_KEY` | Gemini API 키 | 필수 |
| `GEMINI_MODEL` | 사용할 Gemini 모델명 | `gemini-2.5-flash-lite` |
| `PORT` | 서버 포트 | `8000` |
| `UVICORN_RELOAD` | 개발 중 자동 재시작 여부 | `false` |
| `CORS_ORIGINS` | 허용할 오리진 목록 | `http://localhost:8000` |
| `DB_PATH` | SQLite 파일 경로 | 로컬: `backend/guesthouse.db`, Docker: `/data/guesthouse.db` |
| `BASE_WEEKDAY_RATE` | 평일 1박 요금 | `184847` |
| `BASE_WEEKEND_RATE` | 주말 1박 요금 | `242612` |
| `BASE_GUESTS` | 기본 인원 | `2` |
| `MAX_GUESTS` | 최대 인원 | `8` |
| `ADULT_EXTRA_FEE` | 추가 인원 요금 | `20000` |
| `BBQ_FEE` | 바비큐 옵션 요금 | `20000` |
| `TOSSPAYMENTS_WIDGET_CLIENT_KEY` | 토스 위젯 클라이언트 키 | 결제 기능 사용 시 필수 |
| `TOSSPAYMENTS_PAYMENT_METHOD_VARIANT_KEY` | 토스 결제 UI variantKey | `DEFAULT` |
| `TOSSPAYMENTS_SECRET_KEY` | 토스 시크릿 키 | 결제 기능 사용 시 필수 |
| `TOSSPAYMENTS_API_BASE` | 토스 API 기본 주소 | `https://api.tosspayments.com` |
| `PAYMENT_TERMS_VERSION` | 약관 스냅샷 버전 | `2026-03-09-v1` |
| `BOOKED_STATUSES` | 예약 완료로 보는 상태 목록 | `confirming,confirmed,paid` |
| `HOLIDAY_DATES` | 수동 공휴일 목록 | 선택 |
| `ADMIN_DASHBOARD_TOKEN` | 관리자 인증 토큰 | 관리자 기능 사용 시 필수 |

## 주요 API

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET` | `/api/health` | 서버 상태 확인 |
| `GET` | `/api/calendar/config` | 요금 및 공휴일 설정 조회 |
| `GET` | `/api/calendar/availability` | 예약 불가 날짜 조회 |
| `POST` | `/api/payment/quote` | 예약 금액 견적 계산 |
| `GET` | `/api/payment/config` | 토스 결제 설정 조회 |
| `POST` | `/api/payment/prepare` | 주문 생성 및 결제 준비 |
| `GET` | `/reservation/success` | 결제 성공 콜백 |
| `GET` | `/reservation/fail` | 결제 실패 콜백 |
| `POST` | `/api/reservation/check` | 이름과 연락처로 예약 조회 |
| `GET` | `/api/admin/date-blocks` | 예약 차단일 목록 조회 |
| `POST` | `/api/admin/date-blocks` | 예약 차단일 추가 또는 수정 |
| `DELETE` | `/api/admin/date-blocks/{block_id}` | 예약 차단일 삭제 |
| `GET` | `/api/admin/reservations` | 예약 목록 조회 |
| `POST` | `/api/admin/cancel-payment` | 결제 취소 |
| `POST` | `/api/chat` | 챗봇 SSE 스트리밍 응답 |

---

## 데이터 저장 구조

SQLite를 사용하며, 주요 테이블은 아래와 같습니다.

| 테이블 | 용도 |
|---|---|
| `chat_logs` | 챗봇 대화 기록 |
| `payment_intents` | 예약 및 결제 상태 관리 |
| `payment_term_consents` | 약관 동의 스냅샷 저장 |
| `admin_date_blocks` | 관리자 예약 차단일 저장 |

## GitHub 업로드 기준

저장소에 **올려야 하는 것**:

- 애플리케이션 소스코드
- `Dockerfile`
- `compose.yml`
- `.dockerignore`
- `requirements.txt`
- `README.md`
- `.env.example`

저장소에 **올리면 안 되는 것**:

- `backend/.env`
- 실제 SQLite DB 파일
- 로그 파일
- 인증서
- 운영 서버 전용 비밀값

---

## 운영 메모

- mini PC 배포 시에는 `backend/.env`와 `data/`만 잘 보존하면 복구가 단순해집니다.
- SQLite를 계속 사용할 계획이라면 `data/guesthouse.db` 정기 백업이 필요합니다.
- 운영 환경에서는 Nginx 또는 Caddy 같은 리버스 프록시를 앞단에 두는 구성이 적절합니다.
- `docs/archive/`는 실행 필수 파일이 아니며 참고 자료 성격입니다.

## 배포 복구 절차

새 서버 또는 초기화 이후 복구는 보통 아래 순서로 진행하면 됩니다.

```bash
git clone <repository>
cp backend/.env.example backend/.env
# 실제 운영값으로 backend/.env 수정
docker compose up -d --build
```

기존 데이터가 있다면 `data/guesthouse.db`를 함께 복원하면 됩니다.

