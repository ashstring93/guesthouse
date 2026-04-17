"""API 요청 모델."""

from pydantic import BaseModel, ConfigDict


class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "체크인 시간은 언제인가요?",
                "session_id": "session_12345",
            }
        }
    )


class PaymentQuoteRequest(BaseModel):
    checkin_date: str
    nights: int = 1
    adults: int = 2
    bbq: bool = False
    pet_with: bool = False


class PaymentPrepareRequest(BaseModel):
    customer_name: str
    customer_phone: str
    checkin_date: str
    nights: int = 1
    adults: int = 2
    bbq: bool = False
    pet_with: bool = False
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


class CancelPaymentRequest(BaseModel):
    order_id: str
    cancel_reason: str = "고객 요청에 의한 취소"


class AdminDateBlockRequest(BaseModel):
    start_date: str
    end_date: str | None = None
    reason: str = ""
