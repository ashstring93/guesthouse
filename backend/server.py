import json
import os
import uuid
import sqlite3
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from chatbot import GuestHouseChatbot

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
RESERVATION_PAGES_DIR = FRONTEND_DIR / "pages" / "reservation"

# 루트 .env와 backend/.env를 모두 로드하고 backend 값을 우선 적용합니다.
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env", override=True)

chatbot = None
DB_PATH = BACKEND_DIR / "chatbot_logs.db"

BASE_WEEKDAY_RATE = int(os.getenv("BASE_WEEKDAY_RATE", "150000"))
BASE_WEEKEND_RATE = int(os.getenv("BASE_WEEKEND_RATE", "200000"))
BASE_GUESTS = int(os.getenv("BASE_GUESTS", "2"))
MAX_GUESTS = int(os.getenv("MAX_GUESTS", "6"))
ADULT_EXTRA_FEE = int(os.getenv("ADULT_EXTRA_FEE", "20000"))
CHILD_EXTRA_FEE = int(os.getenv("CHILD_EXTRA_FEE", "10000"))
INFANT_EXTRA_FEE = int(os.getenv("INFANT_EXTRA_FEE", "5000"))
BBQ_FEE = int(os.getenv("BBQ_FEE", "20000"))
PAYMENT_CHECKOUT_URL = os.getenv("PAYMENT_CHECKOUT_URL", "").strip()
DEFAULT_HOLIDAY_DATES = {
    "2026-01-01",
    "2026-02-16",
    "2026-02-17",
    "2026-02-18",
    "2026-03-01",
    "2026-03-02",
    "2026-05-05",
    "2026-05-24",
    "2026-05-25",
    "2026-06-03",
    "2026-06-06",
    "2026-07-17",
    "2026-08-17",
    "2026-09-24",
    "2026-09-25",
    "2026-09-26",
    "2026-10-03",
    "2026-10-05",
    "2026-10-09",
    "2026-12-25",
}

ENV_HOLIDAY_DATES = {
    value.strip()
    for value in os.getenv("HOLIDAY_DATES", "").split(",")
    if value.strip()
}
HOLIDAY_DATES = DEFAULT_HOLIDAY_DATES | ENV_HOLIDAY_DATES
TERMS_VERSION = os.getenv("PAYMENT_TERMS_VERSION", "2026-02-24-v1").strip()
BOOKED_STATUS_FILTER = tuple(
    status.strip().lower()
    for status in os.getenv("BOOKED_STATUSES", "pending,confirmed,paid").split(",")
    if status.strip()
)

PAYMENT_TERMS_CATALOG = {
    "policy": {
        "title": "유의사항/환불규정 동의",
        "snapshot_text": (
            "체크인/체크아웃 및 환불 기준: 7일 전 전액 환불, 6~3일 전 50%, 2일 이내 환불 불가."
        ),
    },
    "privacy": {
        "title": "개인정보 수집 및 이용동의",
        "snapshot_text": (
            "수집 항목(예약자명/연락처/결제확인정보), 이용 목적(예약·결제·문의 대응), 법정 보유기간 보관."
        ),
    },
    "thirdparty": {
        "title": "개인정보 제3자 제공동의",
        "snapshot_text": (
            "제공 대상(PG/카드사/간편결제사), 제공 항목(주문번호/결제금액 등), 제공 목적(승인·정산·환불)."
        ),
    },
    "adult": {
        "title": "미성년자 아님 동의",
        "snapshot_text": "예약자는 본인이며 미성년자가 아니고 본인 명의로 예약/결제를 진행합니다.",
    },
}


def init_db():
    """Initialize local SQLite tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            session_id TEXT,
            question TEXT,
            answer TEXT
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS payment_intents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            order_id TEXT UNIQUE,
            customer_name TEXT,
            customer_phone TEXT,
            checkin_date TEXT,
            nights INTEGER,
            adults INTEGER,
            extra_guests INTEGER,
            room_amount INTEGER,
            extra_amount INTEGER,
            total_amount INTEGER,
            payment_method TEXT,
            status TEXT,
            payload TEXT
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS payment_term_consents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            order_id TEXT,
            term_key TEXT,
            term_title TEXT,
            term_version TEXT,
            agreed INTEGER,
            agreed_at DATETIME,
            client_ip TEXT,
            snapshot_text TEXT
        )
    """
    )
    conn.commit()
    conn.close()


def log_chat(session_id: str, question: str, answer: str):
    """Persist chat logs into SQLite."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_logs (session_id, question, answer) VALUES (?, ?, ?)",
            (session_id, question, answer),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Logging Error: {e}")


def create_order_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"MBA-{timestamp}-{uuid.uuid4().hex[:6].upper()}"


def parse_date_or_400(date_str: str) -> date:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="checkin_date 형식이 올바르지 않습니다. (YYYY-MM-DD)",
        ) from exc


def parse_iso_date_or_400(date_str: str, field_name: str) -> date:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} 형식이 올바르지 않습니다. (YYYY-MM-DD)",
        ) from exc


def normalize_phone(value: str) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def calculate_room_amount(checkin_date: date, nights: int) -> int:
    def is_holiday(d: date) -> bool:
        return d.isoformat() in HOLIDAY_DATES

    def is_premium_rate_day(d: date) -> bool:
        # 금/토 체크인, 공휴일 전날 체크인은 프리미엄 요금입니다.
        # 공휴일 당일도 다음 날이 평일이 아니면 휴일 요금으로 처리합니다.
        next_day = d + timedelta(days=1)
        is_before_holiday = is_holiday(next_day)

        next_day_is_plain_weekday = next_day.weekday() not in (5, 6) and not is_holiday(
            next_day
        )
        holiday_day_premium = is_holiday(d) and not next_day_is_plain_weekday

        return d.weekday() in (4, 5) or is_before_holiday or holiday_day_premium

    total = 0
    for offset in range(nights):
        d = checkin_date + timedelta(days=offset)
        total += BASE_WEEKEND_RATE if is_premium_rate_day(d) else BASE_WEEKDAY_RATE
    return total


def calculate_extra_guest_details(
    adults: int, children: int, infants: int, nights: int
) -> dict:
    """Calculate additional guest fees by age group after base guest allowance."""
    remaining_free = max(0, BASE_GUESTS)

    free_adults = min(adults, remaining_free)
    remaining_free -= free_adults

    free_children = min(children, remaining_free)
    remaining_free -= free_children

    free_infants = min(infants, remaining_free)
    remaining_free -= free_infants

    charged_adults = max(0, adults - free_adults)
    charged_children = max(0, children - free_children)
    charged_infants = max(0, infants - free_infants)

    per_night_extra = (
        charged_adults * ADULT_EXTRA_FEE
        + charged_children * CHILD_EXTRA_FEE
        + charged_infants * INFANT_EXTRA_FEE
    )
    extra_amount = per_night_extra * max(1, nights)

    return {
        "charged_adults": charged_adults,
        "charged_children": charged_children,
        "charged_infants": charged_infants,
        "extra_guests": charged_adults + charged_children + charged_infants,
        "extra_amount": extra_amount,
    }


def save_payment_intent(intent: dict):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO payment_intents (
                order_id, customer_name, customer_phone, checkin_date, nights, adults,
                extra_guests, room_amount, extra_amount, total_amount,
                payment_method, status, payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                intent["order_id"],
                intent.get("customer_name"),
                intent.get("customer_phone"),
                intent["checkin_date"],
                intent["nights"],
                intent.get("total_guests", intent.get("adults", 0)),
                intent["extra_guests"],
                intent["room_amount"],
                intent["extra_amount"],
                intent["total_amount"],
                intent["payment_method"],
                intent["status"],
                json.dumps(intent, ensure_ascii=False),
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Payment intent save error: {e}")


def save_payment_term_consents(
    order_id: str,
    consents: dict[str, bool],
    term_version: str,
    client_ip: str | None = None,
):
    try:
        agreed_at = datetime.now().isoformat(timespec="seconds")
        rows = []
        for term_key, term in PAYMENT_TERMS_CATALOG.items():
            rows.append(
                (
                    order_id,
                    term_key,
                    term["title"],
                    term_version,
                    1 if consents.get(term_key, False) else 0,
                    agreed_at,
                    client_ip,
                    term["snapshot_text"],
                )
            )

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT INTO payment_term_consents (
                order_id, term_key, term_title, term_version, agreed, agreed_at, client_ip, snapshot_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            rows,
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Payment term consent save error: {e}")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize and clean up chatbot lifecycle."""
    global chatbot

    init_db()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경 변수가 설정되어야 합니다.")

    chatbot = GuestHouseChatbot(api_key=api_key)
    print("챗봇 초기화 완료")
    print("  model: gemini-2.5-flash-lite")
    print("  RAG 기반 문서 컨텍스트 로드 완료")
    print(f"  DB 로그 경로: {DB_PATH}")
    print(f"  holiday count: {len(HOLIDAY_DATES)} (manual)")

    try:
        yield
    finally:
        chatbot = None


app = FastAPI(
    title="물레방아하우스 챗봇 API",
    description="Gemini 2.5 Flash-Lite 기반 게스트하우스 Q&A 챗봇",
    version="1.0.0",
    lifespan=lifespan,
)

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
app.mount("/images", StaticFiles(directory=str(FRONTEND_DIR / "images")), name="images")
app.mount("/fonts", StaticFiles(directory=str(FRONTEND_DIR / "fonts")), name="fonts")


class ChatRequest(BaseModel):
    question: str
    session_id: str = None  # 대화 세션 아이디

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "체크인 시간은 언제인가요?",
                "session_id": "session_12345",
            }
        }
    )


class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: list[str]


class PaymentQuoteRequest(BaseModel):
    checkin_date: str
    nights: int = 1
    adults: int = 2
    children: int = 0
    infants: int = 0
    bbq: bool = False
    pet_with: bool = False


class PaymentPrepareRequest(BaseModel):
    customer_name: str
    customer_phone: str
    checkin_date: str
    nights: int = 1
    adults: int = 2
    children: int = 0
    infants: int = 0
    bbq: bool = False
    pet_with: bool = False
    payment_method: str = "card"
    agreed_to_terms: bool = False
    terms_version: str | None = None
    agree_policy: bool = False
    agree_privacy: bool = False
    agree_thirdparty: bool = False
    agree_adult: bool = False
    arrival_time: str | None = None
    request_note: str | None = None


class ReservationCheckRequest(BaseModel):
    customer_name: str
    customer_phone: str


@app.get("/")
async def root():
    """웹사이트 메인 페이지."""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/reservation/book")
async def reservation_book_redirect(request: Request):
    """예약/결제 페이지 슬래시 URL로 정규화."""
    target = "book/"
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(url=target, status_code=307)


@app.get("/reservation/book/")
async def reservation_book_page():
    """예약/결제용 페이지."""
    return FileResponse(RESERVATION_PAGES_DIR / "book.html")


@app.get("/reservation/list")
async def reservation_list_redirect(request: Request):
    """예약 현황 페이지 슬래시 URL로 정규화."""
    target = "list/"
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(url=target, status_code=307)


@app.get("/reservation/list/")
async def reservation_list_page():
    """예약 현황 페이지."""
    return FileResponse(RESERVATION_PAGES_DIR / "list.html")


@app.get("/reservation/check")
async def reservation_check_redirect(request: Request):
    """예약 확인 페이지 슬래시 URL로 정규화."""
    target = "check/"
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(url=target, status_code=307)


@app.get("/reservation/check/")
async def reservation_check_page():
    """예약 확인 페이지."""
    return FileResponse(RESERVATION_PAGES_DIR / "check.html")


@app.get("/reservation-pay.html")
async def reservation_pay_page(request: Request):
    """구형 예약 경로 호환용 리다이렉트."""
    target = "reservation/book/"
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(url=target, status_code=307)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Favicon 404 에러 방지를 위한 빈 응답."""
    from fastapi import Response

    return Response(status_code=204)


@app.get("/api/health")
async def health_check():
    """헬스체크."""
    return {"status": "healthy", "chatbot_loaded": chatbot is not None}


@app.get("/api/calendar/config")
async def calendar_config():
    """캘린더 요금 기본값과 공휴일 설정."""
    return {
        "holiday_dates": sorted(HOLIDAY_DATES),
        "base_weekday_rate": BASE_WEEKDAY_RATE,
        "base_weekend_rate": BASE_WEEKEND_RATE,
    }


@app.get("/api/calendar/availability")
async def calendar_availability(
    start: str = Query(..., description="조회 시작일(YYYY-MM-DD)"),
    end: str = Query(..., description="조회 종료일(YYYY-MM-DD)"),
):
    """예약 현황 달력용 마감일 목록."""
    start_date = parse_iso_date_or_400(start, "start")
    end_date = parse_iso_date_or_400(end, "end")

    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end는 start 이후 날짜여야 합니다.")
    if (end_date - start_date).days > 730:
        raise HTTPException(status_code=400, detail="조회 기간은 최대 730일입니다.")

    query = """
        SELECT checkin_date, nights, status
        FROM payment_intents
        WHERE checkin_date IS NOT NULL
          AND nights IS NOT NULL
    """
    params: list[str] = []
    if BOOKED_STATUS_FILTER:
        placeholders = ",".join(["?"] * len(BOOKED_STATUS_FILTER))
        query += f" AND lower(status) IN ({placeholders})"
        params.extend(BOOKED_STATUS_FILTER)

    booked_dates: set[str] = set()
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
    finally:
        conn.close()

    for checkin_str, nights_value, _status in rows:
        try:
            checkin = datetime.strptime(str(checkin_str), "%Y-%m-%d").date()
            nights = int(nights_value)
        except (ValueError, TypeError):
            continue

        if nights <= 0:
            continue

        for offset in range(nights):
            target = checkin + timedelta(days=offset)
            if start_date <= target <= end_date:
                booked_dates.add(target.isoformat())

    return {
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "booked_dates": sorted(booked_dates),
    }


@app.post("/api/payment/quote")
async def payment_quote(request: PaymentQuoteRequest):
    """예약 요금 견적."""
    checkin = parse_date_or_400(request.checkin_date)
    nights = max(1, min(request.nights, 5))
    adults = max(0, request.adults)
    children = max(0, request.children)
    infants = max(0, request.infants)
    total_guests = adults + children + infants

    if total_guests <= 0:
        raise HTTPException(
            status_code=400, detail="총 인원은 최소 1명 이상이어야 합니다."
        )
    if total_guests > MAX_GUESTS:
        raise HTTPException(
            status_code=400,
            detail=f"총 인원은 최대 {MAX_GUESTS}명까지 예약할 수 있습니다.",
        )

    room_amount = calculate_room_amount(checkin, nights)
    extra_detail = calculate_extra_guest_details(adults, children, infants, nights)
    bbq_amount = BBQ_FEE if bool(request.bbq) else 0
    total_amount = room_amount + extra_detail["extra_amount"] + bbq_amount

    return {
        "checkin_date": checkin.isoformat(),
        "nights": nights,
        "adults": adults,
        "children": children,
        "infants": infants,
        "total_guests": total_guests,
        "extra_guests": extra_detail["extra_guests"],
        "charged_adults": extra_detail["charged_adults"],
        "charged_children": extra_detail["charged_children"],
        "charged_infants": extra_detail["charged_infants"],
        "room_amount": room_amount,
        "extra_amount": extra_detail["extra_amount"],
        "bbq_amount": bbq_amount,
        "total_amount": total_amount,
        "currency": "KRW",
        "base_weekday_rate": BASE_WEEKDAY_RATE,
        "base_weekend_rate": BASE_WEEKEND_RATE,
        "adult_extra_fee": ADULT_EXTRA_FEE,
        "child_extra_fee": CHILD_EXTRA_FEE,
        "infant_extra_fee": INFANT_EXTRA_FEE,
        "bbq_fee": BBQ_FEE,
    }


@app.post("/api/payment/prepare")
async def payment_prepare(request: PaymentPrepareRequest, http_request: Request):
    """주문 생성 및 결제 준비.

    NOTE: 실제 PG 연동 전 단계입니다.
    PAYMENT_CHECKOUT_URL 환경변수가 없으면 주문 생성만 수행하고 관리자 문의로 마무리됩니다.
    """
    required_consents = {
        "policy": request.agree_policy,
        "privacy": request.agree_privacy,
        "thirdparty": request.agree_thirdparty,
        "adult": request.agree_adult,
    }
    if not request.agreed_to_terms or not all(required_consents.values()):
        raise HTTPException(status_code=400, detail="필수 약관 동의가 필요합니다.")

    term_version = (request.terms_version or TERMS_VERSION).strip() or TERMS_VERSION
    client_ip = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent", "")

    checkin = parse_date_or_400(request.checkin_date)
    nights = max(1, min(request.nights, 5))
    adults = max(0, request.adults)
    children = max(0, request.children)
    infants = max(0, request.infants)
    total_guests = adults + children + infants

    if total_guests <= 0:
        raise HTTPException(
            status_code=400, detail="총 인원은 최소 1명 이상이어야 합니다."
        )
    if total_guests > MAX_GUESTS:
        raise HTTPException(
            status_code=400,
            detail=f"총 인원은 최대 {MAX_GUESTS}명까지 예약할 수 있습니다.",
        )

    room_amount = calculate_room_amount(checkin, nights)
    extra_detail = calculate_extra_guest_details(adults, children, infants, nights)
    bbq_amount = BBQ_FEE if bool(request.bbq) else 0
    total_amount = room_amount + extra_detail["extra_amount"] + bbq_amount

    order_id = create_order_id()
    intent = {
        "order_id": order_id,
        "customer_name": request.customer_name.strip(),
        "customer_phone": request.customer_phone.strip(),
        "checkin_date": checkin.isoformat(),
        "nights": nights,
        "adults": adults,
        "children": children,
        "infants": infants,
        "total_guests": total_guests,
        "bbq": bool(request.bbq),
        "pet_with": bool(request.pet_with),
        "extra_guests": extra_detail["extra_guests"],
        "charged_adults": extra_detail["charged_adults"],
        "charged_children": extra_detail["charged_children"],
        "charged_infants": extra_detail["charged_infants"],
        "room_amount": room_amount,
        "extra_amount": extra_detail["extra_amount"],
        "bbq_amount": bbq_amount,
        "total_amount": total_amount,
        "payment_method": request.payment_method,
        "terms_version": term_version,
        "consents": required_consents,
        "arrival_time": (request.arrival_time or "").strip(),
        "request_note": (request.request_note or "").strip(),
        "client_ip": client_ip,
        "user_agent": user_agent,
        "status": "pending",
    }
    save_payment_intent(intent)
    save_payment_term_consents(order_id, required_consents, term_version, client_ip)

    checkout_url = PAYMENT_CHECKOUT_URL or None
    return {
        "order_id": order_id,
        "checkout_url": checkout_url,
        "amount": total_amount,
        "currency": "KRW",
        "message": (
            "결제 페이지로 이동합니다."
            if checkout_url
            else "현재 결제 연동 준비 중입니다. 주문이 접수되었고 관리자 확인 후 안내드립니다."
        ),
    }


@app.post("/api/reservation/check")
async def reservation_check(request: ReservationCheckRequest):
    """예약자명 + 연락처로 최신 예약 건을 조회합니다."""
    customer_name = request.customer_name.strip()
    phone_digits = normalize_phone(request.customer_phone)

    if not customer_name:
        raise HTTPException(status_code=400, detail="customer_name을 입력해 주세요.")
    if not phone_digits:
        raise HTTPException(status_code=400, detail="customer_phone을 입력해 주세요.")

    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT order_id, status, checkin_date, nights, adults, total_amount,
                   payment_method, created_at, customer_phone, payload
            FROM payment_intents
            WHERE trim(customer_name) = ?
            ORDER BY id DESC
        """,
            (customer_name,),
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="예약 정보를 찾을 수 없습니다.")

    row = None
    for candidate in rows:
        if normalize_phone(candidate[8]) == phone_digits:
            row = candidate
            break

    if not row:
        raise HTTPException(status_code=404, detail="예약 정보를 찾을 수 없습니다.")

    (
        found_order_id,
        status,
        checkin_date,
        nights,
        total_guests,
        total_amount,
        payment_method,
        created_at,
        _customer_phone,
        payload_raw,
    ) = row

    payload = {}
    if payload_raw:
        try:
            payload = json.loads(payload_raw)
        except (TypeError, json.JSONDecodeError):
            payload = {}

    adults = int(payload.get("adults", total_guests or 0) or 0)
    children = int(payload.get("children", 0) or 0)
    infants = int(payload.get("infants", 0) or 0)
    bbq = bool(payload.get("bbq", False))
    pet_with = bool(payload.get("pet_with", False))

    return {
        "order_id": found_order_id,
        "status": status,
        "checkin_date": checkin_date,
        "nights": int(nights or 1),
        "adults": adults,
        "children": children,
        "infants": infants,
        "total_guests": int(total_guests or adults + children + infants),
        "bbq": bbq,
        "pet_with": pet_with,
        "total_amount": int(total_amount or 0),
        "payment_method": payment_method or "card",
        "created_at": created_at,
    }


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """챗봇 스트리밍 엔드포인트(텍스트 스트림 응답)."""
    if not chatbot:
        raise HTTPException(status_code=503, detail="챗봇이 초기화되지 않았습니다.")

    if not request.question or request.question.strip() == "":
        raise HTTPException(status_code=400, detail="질문을 입력해 주세요.")

    try:
        session_id = request.session_id or str(uuid.uuid4())

        # 스트리밍 응답 생성기 획득 (sources는 미사용)
        generator, _ = chatbot.ask_stream(request.question, session_id)

        # 로그 기록을 위한 스트리밍 래퍼
        def generator_wrapper(gen, question, sid):
            full_answer = ""
            for chunk in gen:
                full_answer += chunk
                yield chunk
            log_chat(sid, question, full_answer)

        # 헤더에는 세션 아이디만 포함
        headers = {
            "X-Session-Id": session_id,
        }

        return StreamingResponse(
            generator_wrapper(generator, request.question, session_id),
            media_type="text/plain",
            headers=headers,
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"Error handling chat request: {e}")
        raise HTTPException(status_code=500, detail=f"오류가 발생했습니다: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    reload_enabled = os.getenv("UVICORN_RELOAD", "false").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    print("=" * 70)
    print("물레방아하우스 챗봇 서버 시작")
    print("=" * 70)
    print(f"  port: {port}")
    print(f"  docs: http://localhost:{port}/docs")
    print(f"  reload: {reload_enabled}")
    print(f"  frontend: {FRONTEND_DIR}")
    print("  static: /js, /css, /images, /fonts")
    print("=" * 70)

    if reload_enabled:
        # reload 모드에서는 import string이 필요합니다.
        uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
    else:
        # 일반 실행은 app 객체를 직접 전달해 모듈 임포트 순서 문제를 피합니다.
        uvicorn.run(app, host="0.0.0.0", port=port, reload=False)
