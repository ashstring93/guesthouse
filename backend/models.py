"""
Pydantic 요청 모델 모듈.

FastAPI 엔드포인트에서 사용하는 Request Body 모델을 정의합니다.
각 모델은 프론트엔드로부터 전달받는 JSON 데이터의 구조를 검증합니다.

사용 예시:
    from models import ChatRequest, PaymentQuoteRequest
"""

from pydantic import BaseModel, ConfigDict


class ChatRequest(BaseModel):
    """챗봇 대화 요청 모델.

    question: 사용자 질문 텍스트
    session_id: 대화 세션 식별자 (없으면 서버에서 자동 생성)
    """

    question: str
    session_id: str = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "체크인 시간은 언제인가요?",
                "session_id": "session_12345",
            }
        }
    )


class PaymentQuoteRequest(BaseModel):
    """요금 견적 요청 모델.

    날짜, 인원, 옵션 정보를 받아 예상 결제 금액을 계산합니다.
    """

    checkin_date: str  # 체크인 날짜 (YYYY-MM-DD)
    nights: int = 1  # 숙박 일수 (1~5)
    adults: int = 2  # 성인 인원
    bbq: bool = False  # BBQ 옵션 사용 여부
    pet_with: bool = False  # 반려동물 동반 여부


class PaymentPrepareRequest(BaseModel):
    """결제 준비(주문 생성) 요청 모델.

    요금 견적 정보에 더해 고객 정보와 약관 동의 상태를 포함합니다.
    모든 필수 약관(policy, privacy, thirdparty, adult)에 동의해야 결제 진행이 가능합니다.
    """

    customer_name: str  # 예약자명
    customer_phone: str  # 예약자 연락처
    checkin_date: str  # 체크인 날짜 (YYYY-MM-DD)
    nights: int = 1  # 숙박 일수
    adults: int = 2  # 성인 인원
    bbq: bool = False  # BBQ 옵션
    pet_with: bool = False  # 반려동물 동반
    agreed_to_terms: bool = False  # 약관 전체 동의 플래그
    terms_version: str | None = None  # 약관 버전 (없으면 서버 기본값 사용)
    agree_policy: bool = False  # 유의사항/환불규정 동의
    agree_privacy: bool = False  # 개인정보 수집 동의
    agree_thirdparty: bool = False  # 제3자 제공 동의
    agree_adult: bool = False  # 미성년자 아님 동의
    arrival_time: str | None = None  # 도착 예정 시간
    request_note: str | None = None  # 요청사항


class ReservationCheckRequest(BaseModel):
    """예약 조회 요청 모델.

    예약자명과 연락처로 최신 예약 건을 검색합니다.
    """

    customer_name: str  # 예약자명
    customer_phone: str  # 예약자 연락처


class CancelPaymentRequest(BaseModel):
    """관리자 결제 취소 요청 모델.

    관리자가 특정 주문을 취소할 때 사용합니다.
    환불 정책(체크인 잔여일 기준)이 자동 적용됩니다.
    """

    order_id: str  # 취소할 주문번호
    cancel_reason: str = "고객 요청에 의한 취소"  # 취소 사유


class AdminDateBlockRequest(BaseModel):
    """관리자 수동 차단 일정 요청 모델.

    관리자가 특정 날짜 또는 날짜 범위를 예약 불가 상태로 잠글 때 사용합니다.
    end_date가 없으면 start_date 하루만 차단합니다.
    """

    start_date: str  # 차단 시작일 (YYYY-MM-DD)
    end_date: str | None = None  # 차단 종료일 (YYYY-MM-DD)
    reason: str = ""  # 차단 사유
