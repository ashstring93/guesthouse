document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('reservation-check-form');
    if (!form) return;

    const nameInput = document.getElementById('check-customer-name');
    const phoneInput = document.getElementById('check-customer-phone');
    const message = document.getElementById('reservation-check-message');
    const resultCard = document.getElementById('reservation-check-result');

    const statusText = document.getElementById('check-status');
    const scheduleText = document.getElementById('check-schedule');
    const guestsText = document.getElementById('check-guests');
    const amountText = document.getElementById('check-amount');
    const bbqText = document.getElementById('check-bbq');
    const petText = document.getElementById('check-pet');
    const methodText = document.getElementById('check-method');
    const createdText = document.getElementById('check-created-at');

    const STATUS_LABELS = {
        pending: '결제 대기',
        confirmed: '예약 확정',
        paid: '결제 완료',
    };

    const PAYMENT_METHOD_LABELS = {
        card: '신용/체크카드',
        naverpay: '네이버페이',
        tosspay: '토스페이',
        kakaopay: '카카오페이',
    };

    const normalizePhone = (value) => String(value || '').replace(/[^0-9]/g, '');

    const formatPhone = (value) => {
        const digits = normalizePhone(value).slice(0, 11);
        if (digits.length < 4) return digits;
        if (digits.length < 8) return `${digits.slice(0, 3)}-${digits.slice(3)}`;
        return `${digits.slice(0, 3)}-${digits.slice(3, 7)}-${digits.slice(7)}`;
    };

    const parseYmd = (value) => {
        const parsed = new Date(`${value}T00:00:00`);
        return Number.isNaN(parsed.getTime()) ? null : parsed;
    };

    const formatSchedule = (checkinDate, nights) => {
        const checkin = parseYmd(checkinDate);
        if (!checkin) return '-';

        const checkout = new Date(checkin);
        checkout.setDate(checkout.getDate() + Number(nights || 1));

        const formatter = new Intl.DateTimeFormat('ko-KR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            weekday: 'short',
        });

        return `${formatter.format(checkin)} ~ ${formatter.format(checkout)} (${nights}박)`;
    };

    const formatKrw = (amount) => `${Number(amount || 0).toLocaleString('ko-KR')}원`;

    const formatCreatedAt = (value) => {
        if (!value) return '-';
        const date = new Date(String(value).replace(' ', 'T'));
        if (Number.isNaN(date.getTime())) return String(value);

        return new Intl.DateTimeFormat('ko-KR', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        }).format(date);
    };

    const setMessage = (text, type) => {
        if (!message) return;
        message.textContent = text || '';
        message.classList.remove('error', 'success');
        if (type) {
            message.classList.add(type);
        }
    };

    const setResultVisible = (visible) => {
        if (!resultCard) return;
        resultCard.hidden = !visible;
    };

    const formatGuests = (payload) => {
        const adults = Number(payload.adults || 0);
        const children = Number(payload.children || 0);
        const infants = Number(payload.infants || 0);
        const total = Number(payload.total_guests || adults + children + infants);
        return `총 ${total}명 (성인 ${adults} / 아동 ${children} / 유아 ${infants})`;
    };

    const renderResult = (payload) => {
        if (statusText) statusText.textContent = STATUS_LABELS[payload.status] || payload.status || '-';
        if (scheduleText) scheduleText.textContent = formatSchedule(payload.checkin_date, payload.nights);
        if (guestsText) guestsText.textContent = formatGuests(payload);
        if (amountText) amountText.textContent = formatKrw(payload.total_amount);
        if (bbqText) bbqText.textContent = payload.bbq ? '이용함' : '이용 안 함';
        if (petText) petText.textContent = payload.pet_with ? '동반' : '미동반';
        if (methodText) {
            methodText.textContent = PAYMENT_METHOD_LABELS[payload.payment_method] || payload.payment_method || '-';
        }
        if (createdText) createdText.textContent = formatCreatedAt(payload.created_at);
    };

    if (phoneInput) {
        phoneInput.addEventListener('input', () => {
            phoneInput.value = formatPhone(phoneInput.value);
        });
    }

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        setResultVisible(false);

        const customerName = nameInput ? nameInput.value.trim() : '';
        const phoneRaw = phoneInput ? phoneInput.value.trim() : '';
        const phoneDigits = normalizePhone(phoneRaw);

        if (!customerName) {
            setMessage('예약자 이름을 입력해 주세요.', 'error');
            if (nameInput) nameInput.focus();
            return;
        }

        if (!/^01[0-9]{8,9}$/.test(phoneDigits)) {
            setMessage('연락처 형식을 확인해 주세요. (예: 01012345678)', 'error');
            if (phoneInput) phoneInput.focus();
            return;
        }

        setMessage('예약 정보를 조회하는 중입니다.');

        try {
            const response = await fetch('/api/reservation/check', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    customer_name: customerName,
                    customer_phone: phoneRaw,
                }),
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || '예약 조회에 실패했습니다.');
            }

            renderResult(data);
            setResultVisible(true);
            setMessage('예약 정보를 찾았습니다.', 'success');
        } catch (error) {
            setResultVisible(false);
            setMessage(error.message || '예약 조회 중 오류가 발생했습니다.', 'error');
        }
    });
});
