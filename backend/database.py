"""
데이터베이스 모듈.

SQLite 커넥션 관리, 테이블 초기화, 그리고 데이터 저장/조회 함수를 제공합니다.
모든 DB 작업은 get_db() 컨텍스트 매니저를 통해 안전하게 처리됩니다.

사용 예시:
    from database import get_db, init_db, save_payment_intent
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta

from config import BOOKED_STATUS_FILTER, DB_PATH, PAYMENT_TERMS_CATALOG


# ── 커넥션 관리 ──


@contextmanager
def get_db():
    """SQLite 커넥션 컨텍스트 매니저.

    WAL 모드 + row_factory 자동 설정으로 안전한 커넥션 관리를 보장합니다.
    사용법:
        with get_db() as conn:
            conn.execute("SELECT ...")
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── 테이블 초기화 ──


def init_db():
    """로컬 SQLite 테이블을 초기화합니다.

    chat_logs, payment_intents, payment_term_consents, admin_date_blocks
    네 테이블을 생성하며, 이미 존재하는 경우 무시합니다.
    """
    with get_db() as conn:
        conn.executescript(
            """
            -- 채팅 로그: 챗봇 대화 내용을 세션별로 기록
            CREATE TABLE IF NOT EXISTS chat_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
                session_id  TEXT,
                question    TEXT,
                answer      TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_chat_session
                ON chat_logs(session_id);

            -- 결제 의도: 예약 정보 + 결제 상태를 통합 관리
            CREATE TABLE IF NOT EXISTS payment_intents (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                order_id        TEXT UNIQUE NOT NULL,
                customer_name   TEXT NOT NULL,
                customer_phone  TEXT NOT NULL,
                checkin_date    TEXT NOT NULL,
                nights          INTEGER NOT NULL DEFAULT 1,
                adults          INTEGER NOT NULL DEFAULT 2,
                extra_guests    INTEGER DEFAULT 0,
                room_amount     INTEGER DEFAULT 0,
                extra_amount    INTEGER DEFAULT 0,
                bbq_amount      INTEGER DEFAULT 0,
                total_amount    INTEGER DEFAULT 0,
                status          TEXT NOT NULL DEFAULT 'pending',
                arrival_time    TEXT,
                request_note    TEXT,
                cancel_reason   TEXT,
                cancelled_at    DATETIME,
                payload         TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_pi_status
                ON payment_intents(status);
            CREATE INDEX IF NOT EXISTS idx_pi_checkin
                ON payment_intents(checkin_date);
            CREATE INDEX IF NOT EXISTS idx_pi_customer
                ON payment_intents(customer_name, customer_phone);

            -- 약관 동의 기록: 결제 시 동의한 약관 내용을 스냅샷으로 보관
            CREATE TABLE IF NOT EXISTS payment_term_consents (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                order_id        TEXT NOT NULL
                    REFERENCES payment_intents(order_id) ON DELETE CASCADE,
                term_key        TEXT NOT NULL,
                term_title      TEXT,
                term_version    TEXT,
                agreed          INTEGER DEFAULT 0,
                agreed_at       DATETIME,
                client_ip       TEXT,
                snapshot_text   TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_ptc_order
                ON payment_term_consents(order_id);

            -- 관리자 수동 차단 일정: 특정 날짜/기간을 예약 불가로 잠금
            CREATE TABLE IF NOT EXISTS admin_date_blocks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                start_date  TEXT NOT NULL,
                end_date    TEXT NOT NULL,
                reason      TEXT DEFAULT '',
                UNIQUE(start_date, end_date),
                CHECK(end_date >= start_date)
            );
            CREATE INDEX IF NOT EXISTS idx_adb_range
                ON admin_date_blocks(start_date, end_date);
        """
        )


def _expand_date_strings(start_date: date, end_date: date) -> set[str]:
    """두 날짜 사이의 ISO 날짜 문자열(종료일 포함) 집합을 생성합니다."""
    if end_date < start_date:
        return set()

    return {
        (start_date + timedelta(days=offset)).isoformat()
        for offset in range((end_date - start_date).days + 1)
    }


def get_booked_date_strings(start_date: date, end_date: date) -> set[str]:
    """예약 상태 기준으로 이미 점유된 날짜 목록을 반환합니다."""
    if end_date < start_date:
        return set()

    query = """
        SELECT checkin_date, nights
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
    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()

    for checkin_str, nights_value in rows:
        try:
            checkin = datetime.strptime(str(checkin_str), "%Y-%m-%d").date()
            nights = int(nights_value)
        except (ValueError, TypeError):
            continue

        if nights <= 0:
            continue

        last_stay_date = checkin + timedelta(days=nights - 1)
        if last_stay_date < start_date or checkin > end_date:
            continue

        overlap_start = max(checkin, start_date)
        overlap_end = min(last_stay_date, end_date)
        booked_dates.update(_expand_date_strings(overlap_start, overlap_end))

    return booked_dates


def get_admin_blocked_date_strings(start_date: date, end_date: date) -> set[str]:
    """관리자가 수동 차단한 날짜 목록을 반환합니다."""
    if end_date < start_date:
        return set()

    blocked_dates: set[str] = set()
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT start_date, end_date
            FROM admin_date_blocks
            WHERE start_date <= ?
              AND end_date >= ?
            ORDER BY start_date ASC, end_date ASC
            """,
            (end_date.isoformat(), start_date.isoformat()),
        ).fetchall()

    for range_start_str, range_end_str in rows:
        try:
            range_start = datetime.strptime(str(range_start_str), "%Y-%m-%d").date()
            range_end = datetime.strptime(str(range_end_str), "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue

        overlap_start = max(range_start, start_date)
        overlap_end = min(range_end, end_date)
        blocked_dates.update(_expand_date_strings(overlap_start, overlap_end))

    return blocked_dates


def get_unavailable_date_strings(start_date: date, end_date: date) -> set[str]:
    """예약 점유일과 관리자 수동 차단일을 합친 예약 불가 날짜를 반환합니다."""
    return get_booked_date_strings(start_date, end_date) | get_admin_blocked_date_strings(
        start_date, end_date
    )


def get_stay_unavailable_date_strings(checkin_date: date, nights: int) -> list[str]:
    """숙박 일정과 겹치는 예약 불가 날짜를 순서대로 반환합니다."""
    safe_nights = max(1, int(nights or 1))
    last_stay_date = checkin_date + timedelta(days=safe_nights - 1)
    unavailable_dates = get_unavailable_date_strings(checkin_date, last_stay_date)

    conflicts: list[str] = []
    for offset in range(safe_nights):
        target = (checkin_date + timedelta(days=offset)).isoformat()
        if target in unavailable_dates:
            conflicts.append(target)

    return conflicts


def list_admin_date_blocks() -> list[dict]:
    """관리자 수동 차단 일정 목록을 반환합니다."""
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, start_date, end_date, reason
            FROM admin_date_blocks
            ORDER BY start_date ASC, end_date ASC, id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def upsert_admin_date_block(start_date: str, end_date: str, reason: str = "") -> dict:
    """관리자 수동 차단 일정을 추가하거나 같은 범위가 있으면 사유만 갱신합니다."""
    with get_db() as conn:
        existing = conn.execute(
            """
            SELECT id
            FROM admin_date_blocks
            WHERE start_date = ? AND end_date = ?
            """,
            (start_date, end_date),
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE admin_date_blocks
                SET reason = ?
                WHERE id = ?
                """,
                (reason, existing["id"]),
            )
            row = conn.execute(
                """
                SELECT id, created_at, start_date, end_date, reason
                FROM admin_date_blocks
                WHERE id = ?
                """,
                (existing["id"],),
            ).fetchone()
        else:
            cursor = conn.execute(
                """
                INSERT INTO admin_date_blocks (start_date, end_date, reason)
                VALUES (?, ?, ?)
                """,
                (start_date, end_date, reason),
            )
            row = conn.execute(
                """
                SELECT id, created_at, start_date, end_date, reason
                FROM admin_date_blocks
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()

    return dict(row)


def delete_admin_date_block(block_id: int) -> bool:
    """관리자 수동 차단 일정을 삭제합니다."""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM admin_date_blocks WHERE id = ?", (block_id,))
        return cursor.rowcount > 0


# ── 채팅 로그 저장 ──


def log_chat(session_id: str, question: str, answer: str):
    """채팅 로그를 SQLite에 저장합니다.

    챗봇 스트리밍 응답이 완료된 후 호출되어,
    세션 ID, 질문, 전체 답변을 한 행으로 기록합니다.
    """
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO chat_logs (session_id, question, answer) VALUES (?, ?, ?)",
                (session_id, question, answer),
            )
    except Exception as e:
        print(f"DB Logging Error: {e}")


# ── 결제 의도 저장 ──


def save_payment_intent(intent: dict):
    """결제 의도(예약 정보)를 DB에 저장합니다.

    프론트엔드에서 결제 준비(prepare) 요청 시 호출되어,
    주문번호, 고객 정보, 요금 내역, 결제 상태를 기록합니다.
    payload 컬럼에는 전체 intent dict를 JSON으로 직렬화하여 보관합니다.
    """
    try:
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO payment_intents (
                    order_id, customer_name, customer_phone, checkin_date,
                    nights, adults, extra_guests,
                    room_amount, extra_amount, bbq_amount, total_amount,
                    status, arrival_time, request_note, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    intent["order_id"],
                    intent.get("customer_name", ""),
                    intent.get("customer_phone", ""),
                    intent["checkin_date"],
                    intent["nights"],
                    intent.get("adults", 0),
                    intent["extra_guests"],
                    intent["room_amount"],
                    intent["extra_amount"],
                    intent.get("bbq_amount", 0),
                    intent["total_amount"],
                    intent["status"],
                    intent.get("arrival_time", ""),
                    intent.get("request_note", ""),
                    json.dumps(intent, ensure_ascii=False),
                ),
            )
    except Exception as e:
        print(f"Payment intent save error: {e}")


# ── 약관 동의 기록 저장 ──


def save_payment_term_consents(
    order_id: str,
    consents: dict[str, bool],
    term_version: str,
    client_ip: str | None = None,
):
    """약관 동의 기록을 DB에 저장합니다.

    결제 준비 시 고객이 동의한 각 약관(policy, privacy, thirdparty, adult)의
    동의 여부, 시각, IP, 약관 텍스트 스냅샷을 개별 행으로 기록합니다.
    법적 증빙을 위해 동의 시점의 약관 내용을 snapshot_text로 보관합니다.
    """
    try:
        agreed_at = datetime.now().isoformat(timespec="seconds")
        rows = [
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
            for term_key, term in PAYMENT_TERMS_CATALOG.items()
        ]
        with get_db() as conn:
            conn.executemany(
                """
                INSERT INTO payment_term_consents (
                    order_id, term_key, term_title, term_version,
                    agreed, agreed_at, client_ip, snapshot_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                rows,
            )
    except Exception as e:
        print(f"Payment term consent save error: {e}")
