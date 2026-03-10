document.addEventListener("DOMContentLoaded", () => {
    const panelTotalGuestsEl = document.getElementById("pay-total-guests");
    const panelRoomAmountEl = document.getElementById("pay-amount-room");
    const extraGuestsEl = document.getElementById("pay-extra-guests");
    const panelExtraAmountEl = document.getElementById("pay-amount-extra");
    const panelBbqAmountEl = document.getElementById("pay-amount-bbq");
    const panelTotalAmountEl = document.getElementById("pay-amount-total");
    const statusMessageEl = document.getElementById("payment-status-message");

    const hiddenCheckinInput = document.getElementById("booking-checkin-date");
    const hiddenNightsInput = document.getElementById("booking-nights");
    const hiddenAdultsInput = document.getElementById("booking-adults");

    const checkinInput = document.getElementById("booking-checkin");
    const nightsSelect = document.getElementById("booking-nights-visible");
    const arrivalTimeSelect = document.getElementById("arrival-time");
    const requestNoteInput = document.getElementById("request-note");
    const bookingDateField = document.querySelector(".booking-date-field");
    const bookingCalendarBackdrop = bookingDateField
        ? bookingDateField.querySelector(".booking-calendar-backdrop")
        : null;
    const bookingCalendarCloseBtn = bookingDateField
        ? bookingDateField.querySelector(".booking-calendar-close")
        : null;

    const customerNameInput = document.getElementById("customer-name");
    const customerPhoneInput = document.getElementById("customer-phone");
    const paySubmitBtn = document.getElementById("pay-submit-btn");

    const guestTotalLabel = document.getElementById("guest-total-label");
    const guestCountInputs = Array.from(document.querySelectorAll(".guest-count-checkbox"));

    const bbqCheckbox = document.getElementById("option-bbq");
    const petCheckbox = document.getElementById("option-pet");
    const optionLabels = Array.from(document.querySelectorAll(".option-check"));

    const agreeAllInput = document.getElementById("agree-all");
    const agreePolicyInput = document.getElementById("agree-policy");
    const agreePrivacyInput = document.getElementById("agree-privacy");
    const agreeThirdpartyInput = document.getElementById("agree-thirdparty");
    const agreeAdultInput = document.getElementById("agree-adult");
    const requiredAgreeInputs = Array.from(document.querySelectorAll(".agree-required"));
    const termViewButtons = Array.from(document.querySelectorAll(".term-view-btn"));

    const termsModal = document.getElementById("terms-modal");
    const termsModalTitle = document.getElementById("terms-modal-title");
    const termsModalMeta = document.getElementById("terms-modal-meta");
    const termsModalBody = document.getElementById("terms-modal-body");
    const termsModalCloseTargets = Array.from(document.querySelectorAll("[data-close-terms-modal]"));
    const termsVersionLabel = document.querySelector(".terms-version");


    const MAX_GUESTS = 8;
    const TERMS_VERSION = "2026-03-09-v1";
    const GUEST_GROUPS = ["adults"];
    const BASE_GUESTS = 2;
    const ADULT_EXTRA_FEE = 20000;
    const BBQ_FEE = 20000;
    const GUEST_MINIMUM = {
        adults: 1,
    };

    const qs = new URLSearchParams(window.location.search);
    const getAppBasePath = () => {
        const path = window.location.pathname;
        const marker = "/reservation/";
        const markerIndex = path.indexOf(marker);
        if (markerIndex >= 0) {
            return path.slice(0, markerIndex);
        }
        if (path === "/") return "";
        return path.endsWith("/") ? path.slice(0, -1) : path;
    };
    const apiUrl = (suffix) => `${getAppBasePath()}${suffix}`;
    const TERM_PREVIEW_ANCHORS = {
        policy: "#policy",
        privacy: "#collection-consent",
        thirdparty: "#thirdparty-consent",
        adult: "#adult-notice",
    };
    const getLegalPreviewUrl = (termKey = "") =>
        `${getAppBasePath()}/legal/preview/${TERM_PREVIEW_ANCHORS[termKey] || ""}`;

    const guestState = {
        adults: 2,
    };

    let lastQuote = null;
    let bookingCalendarController = null;
    let restoreCheckinFocusOnClose = false;
    let suppressCheckinFocusOpen = false;

    // ── 토스페이먼츠 V2 결제위젯 상태 ──
    let tossWidgets = null;
    let isTossInitializing = false;

    /**
     * 토스 결제위젯 초기화 및 금액 업데이트.
     * 최초 호출 시 SDK 초기화 + 위젯 렌더링, 이후 호출 시 금액만 업데이트.
     * @param {number} totalAmount - 결제 총액 (KRW)
     */
    const initOrUpdateTossWidgets = async (totalAmount) => {
        // SDK가 로드되지 않은 경우 무시
        if (typeof TossPayments === 'undefined') {
            console.warn('TossPayments SDK가 로드되지 않았습니다.');
            return;
        }

        // 이미 초기화된 경우 금액만 업데이트
        if (tossWidgets) {
            try {
                await tossWidgets.setAmount({ currency: 'KRW', value: totalAmount });
            } catch (e) {
                console.error('위젯 금액 업데이트 실패:', e);
            }
            return;
        }

        // 중복 초기화 방지
        if (isTossInitializing) return;
        isTossInitializing = true;

        try {
            // 1. 백엔드에서 결제위젯 연동 클라이언트 키 조회
            const configRes = await fetch(apiUrl('/api/payment/config'));
            const configData = await configRes.json();
            const clientKey = configData.client_key;

            if (!clientKey) {
                console.warn('결제위젯 연동 키가 설정되지 않았습니다.');
                return;
            }

            // 2. SDK 초기화 (결제위젯 연동 키 사용)
            const tossPayments = TossPayments(clientKey);

            // 3. 위젯 인스턴스 생성 (비회원 결제 = ANONYMOUS)
            const widgets = tossPayments.widgets({
                customerKey: TossPayments.ANONYMOUS,
            });

            // 4. 결제 금액 설정 (renderPaymentMethods 전에 반드시 호출)
            await widgets.setAmount({ currency: 'KRW', value: totalAmount });

            // 5. 결제 UI 렌더링
            await widgets.renderPaymentMethods({
                selector: '#payment-method',
                variantKey: 'DEFAULT',
            });

            // 6. 약관 UI 렌더링
            await widgets.renderAgreement({
                selector: '#agreement',
                variantKey: 'AGREEMENT',
            });

            tossWidgets = widgets;
        } catch (error) {
            console.error('토스 결제위젯 초기화 실패:', error);
        } finally {
            isTossInitializing = false;
        }
    };

    const TERM_DETAILS = {
        policy: {
            title: "숙소 이용 및 환불규정 동의",
            version: TERMS_VERSION,
            effectiveDate: "2026-03-09",
            html: `
                <div class="terms-modal-section">
                    <h4>숙소 이용 기본 정보</h4>
                    <ul class="terms-modal-list">
                        <li>체크인은 오후 3시 이후, 체크아웃은 오전 11시까지입니다.</li>
                        <li>기준 인원은 2인, 최대 숙박 가능 인원은 8인입니다.</li>
                        <li>기준 인원 초과 시 1인당 1박 20,000원의 추가 요금이 부과됩니다.</li>
                        <li>바비큐 이용 시 20,000원의 추가 요금이 발생합니다.</li>
                        <li>대문 열쇠와 현관 비밀번호는 입실 전날에 별도로 공지합니다.</li>
                    </ul>
                </div>
                <div class="terms-modal-section">
                    <h4>취소·환불 기준</h4>
                    <ul class="terms-modal-list">
                        <li>체크인 7일 전까지 취소하면 결제금액의 100%를 환불합니다.</li>
                        <li>체크인 6일 전부터 3일 전까지 취소하면 결제금액의 50%를 환불합니다.</li>
                        <li>체크인 2일 전부터 당일까지의 취소 및 노쇼는 환불이 어렵습니다.</li>
                    </ul>
                </div>
                <p class="terms-modal-note">
                    현재 문안은 시스템 연동 기준에 맞춘 검토용 초안입니다. 성수기/비수기 운영정책과 숙박업 소비자분쟁해결기준 검토 후 확정하는 것을 권장합니다.
                </p>
            `,
        },
        privacy: {
            title: "개인정보 수집 및 이용동의",
            version: TERMS_VERSION,
            effectiveDate: "2026-03-09",
            html: `
                <div class="terms-modal-section">
                    <h4>수집 항목</h4>
                    <ul class="terms-modal-list">
                        <li>예약자명, 연락처, 체크인 날짜, 숙박일수, 숙박 인원, 결제 관련 확인 정보</li>
                        <li>선택 입력 시 도착 예정 시간, 요청사항, 바비큐/반려동물 관련 정보</li>
                    </ul>
                </div>
                <div class="terms-modal-section">
                    <h4>이용 목적</h4>
                    <ul class="terms-modal-list">
                        <li>예약 확인, 숙박 서비스 제공, 문의 응대</li>
                        <li>결제 처리, 환불 처리, 거래기록 보존</li>
                    </ul>
                </div>
                <div class="terms-modal-section">
                    <h4>보유 기간 및 거부권</h4>
                    <ul class="terms-modal-list">
                        <li>관련 법령에서 정한 기간까지 보관 후 파기합니다.</li>
                        <li>필수 정보 수집에 동의하지 않으면 예약 및 결제 진행이 제한될 수 있습니다.</li>
                    </ul>
                </div>
            `,
        },
        thirdparty: {
            title: "결제 처리 관련 개인정보 제공 동의",
            version: TERMS_VERSION,
            effectiveDate: "2026-03-09",
            html: `
                <div class="terms-modal-section">
                    <h4>제공받는 자</h4>
                    <p>토스페이먼츠(주), 카드사, 은행, 간편결제 사업자 등 고객이 선택한 결제수단 관련 사업자</p>
                </div>
                <div class="terms-modal-section">
                    <h4>제공 항목 및 목적</h4>
                    <ul class="terms-modal-list">
                        <li>제공 항목: 예약자명, 연락처, 주문번호, 결제금액, 결제 승인에 필요한 정보</li>
                        <li>제공 목적: 결제 승인, 정산, 환불 처리, 부정거래 방지</li>
                    </ul>
                </div>
                <p class="terms-modal-note">
                    실제 운영 시에는 제3자 제공 동의가 필요한 구조인지, 처리위탁 고지로 정리할 사안인지 결제 연동 문서와 함께 최종 확인이 필요합니다.
                </p>
            `,
        },
        adult: {
            title: "성인 본인 예약 확인",
            version: TERMS_VERSION,
            effectiveDate: "2026-03-09",
            html: `
                <div class="terms-modal-section">
                    <h4>확인 사항</h4>
                    <ul class="terms-modal-list">
                        <li>예약자는 만 19세 이상 성인이며, 본인 명의로 예약 및 결제를 진행합니다.</li>
                        <li>미성년자가 법정대리인 동의 없이 예약한 사실이 확인되는 경우 예약이 취소되거나 추가 확인이 요청될 수 있습니다.</li>
                        <li>허위 정보 입력으로 발생한 책임은 예약자에게 있습니다.</li>
                    </ul>
                </div>
            `,
        },
    };

    const toYmd = (date) => {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    };

    const parseYmd = (ymd) => {
        const parsed = new Date(`${ymd}T00:00:00`);
        return Number.isNaN(parsed.getTime()) ? null : parsed;
    };

    const parseBoolean = (value) =>
        ["1", "true", "yes", "on"].includes(String(value || "").trim().toLowerCase());

    const formatKrw = (amount) => `${Number(amount || 0).toLocaleString("ko-KR")}원`;

    const setStatus = (text, type = "") => {
        if (!statusMessageEl) return;
        statusMessageEl.textContent = text || "";
        statusMessageEl.classList.remove("error", "success");
        if (type) {
            statusMessageEl.classList.add(type);
        }
    };

    const syncCheckinInputs = (checkinDate) => {
        const safeCheckin = String(checkinDate || "");
        if (checkinInput) checkinInput.value = safeCheckin;
        if (hiddenCheckinInput) hiddenCheckinInput.value = safeCheckin;
    };

    const syncNightsInputs = (nights) => {
        const safeNights = String(Math.min(5, Math.max(1, Number(nights || 1))));
        if (nightsSelect) nightsSelect.value = safeNights;
        if (hiddenNightsInput) hiddenNightsInput.value = safeNights;
    };

    const syncCalendarSelection = () => {
        if (!bookingCalendarController) return;
        bookingCalendarController.setSelection({
            checkinDate: hiddenCheckinInput ? hiddenCheckinInput.value : "",
            nights: Number(hiddenNightsInput ? hiddenNightsInput.value : 1),
        });
    };

    const onCalendarOpenChange = (isOpen) => {
        if (checkinInput) {
            checkinInput.setAttribute("aria-expanded", String(Boolean(isOpen)));
        }

        if (!isOpen && restoreCheckinFocusOnClose && checkinInput) {
            restoreCheckinFocusOnClose = false;
            suppressCheckinFocusOpen = true;
            checkinInput.focus();
            window.setTimeout(() => {
                suppressCheckinFocusOpen = false;
            }, 0);
        }
    };

    const openBookingCalendar = () => {
        if (!bookingCalendarController) return;
        syncCalendarSelection();
        bookingCalendarController.open();
    };

    const closeBookingCalendar = (restoreFocus = false) => {
        const isCalendarOpen = Boolean(
            bookingDateField && bookingDateField.classList.contains("is-calendar-open")
        );
        restoreCheckinFocusOnClose = restoreFocus && isCalendarOpen;
        if (!bookingCalendarController) {
            if (restoreCheckinFocusOnClose) {
                suppressCheckinFocusOpen = true;
                checkinInput?.focus();
                window.setTimeout(() => {
                    suppressCheckinFocusOpen = false;
                }, 0);
            }
            return;
        }
        bookingCalendarController.close();
    };

    const resolveInitialStay = (preferredCheckin, preferredNights) => {
        if (!bookingCalendarController) {
            return {
                checkinDate: preferredCheckin,
                nights: preferredNights,
            };
        }

        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const startDate = parseYmd(preferredCheckin) || new Date(today);
        startDate.setHours(0, 0, 0, 0);
        if (startDate < today) {
            startDate.setTime(today.getTime());
        }

        const tryFindStay = (targetNights) => {
            for (let offset = 0; offset < 540; offset += 1) {
                const candidate = new Date(startDate);
                candidate.setDate(startDate.getDate() + offset);
                const candidateDate = toYmd(candidate);
                const validation = bookingCalendarController.validateStay({
                    checkinDate: candidateDate,
                    nights: targetNights,
                });
                if (validation.ok) {
                    return {
                        checkinDate: candidateDate,
                        nights: validation.nights,
                    };
                }
            }
            return null;
        };

        return (
            tryFindStay(preferredNights) ||
            tryFindStay(1) || {
                checkinDate: "",
                nights: 1,
            }
        );
    };

    const formatPhone = (value) => {
        const digits = String(value || "").replace(/[^0-9]/g, "").slice(0, 11);
        if (digits.length < 4) return digits;
        if (digits.length < 8) return `${digits.slice(0, 3)}-${digits.slice(3)}`;
        return `${digits.slice(0, 3)}-${digits.slice(3, 7)}-${digits.slice(7)}`;
    };

    const normalizePhone = (value) => String(value || "").replace(/[^0-9]/g, "");


    const getGuestTotal = () => guestState.adults;

    const getGroupInputs = (group) =>
        guestCountInputs
            .filter((input) => input.dataset.guestGroup === group)
            .sort((a, b) => Number(a.value) - Number(b.value));

    const setGroupSelection = (group, count) => {
        const targetCount = Number(count);
        const inputs = getGroupInputs(group);
        let matched = false;

        inputs.forEach((input) => {
            const checked = Number(input.value) === targetCount;
            input.checked = checked;
            const item = input.closest(".guest-check-item");
            if (item) item.classList.toggle("active", checked);
            if (checked) matched = true;
        });

        if (!matched && inputs.length > 0) {
            const fallback = inputs[0];
            fallback.checked = true;
            const item = fallback.closest(".guest-check-item");
            if (item) item.classList.add("active");
            guestState[group] = Number(fallback.value);
        }
    };

    const syncOptionChecks = () => {
        optionLabels.forEach((label) => {
            const input = label.querySelector('input[type="checkbox"]');
            if (!input) return;
            label.classList.toggle("active", input.checked);
        });
    };


    const escapeHtml = (value) =>
        String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");

    const closeTermsModal = () => {
        if (!termsModal || termsModal.hidden) return;
        termsModal.hidden = true;
        document.body.classList.remove("modal-open");
    };

    const openTermsModal = (termKey) => {
        if (!termsModal || !termsModalTitle || !termsModalMeta || !termsModalBody) return;
        const detail = TERM_DETAILS[termKey];
        if (!detail) return;

        termsModalTitle.textContent = detail.title;
        termsModalMeta.innerHTML = `
            <span>정책 버전 ${escapeHtml(detail.version)} · 기준일 ${escapeHtml(detail.effectiveDate)}</span>
            <a href="${escapeHtml(getLegalPreviewUrl(termKey))}" target="_blank" rel="noopener">전체 운영 문안 보기</a>
        `;
        termsModalBody.innerHTML = detail.html;

        termsModal.hidden = false;
        document.body.classList.add("modal-open");
    };

    const syncAgreeAll = () => {
        if (!agreeAllInput) return;
        agreeAllInput.checked = requiredAgreeInputs.every((input) => input.checked);
    };

    const syncGuestUi = () => {
        if (hiddenAdultsInput) hiddenAdultsInput.value = String(guestState.adults);

        GUEST_GROUPS.forEach((group) => {
            setGroupSelection(group, guestState[group]);
        });

        const total = getGuestTotal();
        if (guestTotalLabel) guestTotalLabel.textContent = `총 ${total}인 / 최대 ${MAX_GUESTS}인`;
        if (panelTotalGuestsEl) panelTotalGuestsEl.textContent = `${total}명`;
    };

    const adjustGuestWithinLimit = () => {
        while (getGuestTotal() > MAX_GUESTS) {
            if (guestState.adults > GUEST_MINIMUM.adults) {
                guestState.adults -= 1;
                continue;
            }
            break;
        }
    };

    const calculateExtraByGroup = (nights, adults, feeMeta = {}) => {
        const safeNights = Math.max(1, Number(nights || 1));

        const extraGuests = Math.max(0, adults - BASE_GUESTS);

        const adultFee = Number.isFinite(Number(feeMeta.adult_extra_fee))
            ? Number(feeMeta.adult_extra_fee)
            : ADULT_EXTRA_FEE;
        const bbqFee = Number.isFinite(Number(feeMeta.bbq_fee))
            ? Number(feeMeta.bbq_fee)
            : BBQ_FEE;

        const extraAmount = extraGuests * adultFee * safeNights;
        const bbqAmount = bbqCheckbox && bbqCheckbox.checked ? bbqFee : 0;

        return {
            extraGuests,
            extraAmount,
            bbqAmount,
        };
    };

    const applyQuote = (quote) => {
        const safeQuote = quote && typeof quote === "object" ? quote : {};
        const roomAmount = Number(safeQuote.room_amount || 0);
        const nights = Number(safeQuote.nights || hiddenNightsInput?.value || 1);
        const extraInfo = calculateExtraByGroup(
            nights,
            guestState.adults,
            0,
            0,
            safeQuote
        );
        const totalAmount = roomAmount + extraInfo.extraAmount + extraInfo.bbqAmount;
        lastQuote = {
            ...safeQuote,
            nights,
            room_amount: roomAmount,
            extra_amount: extraInfo.extraAmount,
            bbq_amount: extraInfo.bbqAmount,
            extra_guests: extraInfo.extraGuests,
            total_amount: totalAmount,
        };

        syncCheckinInputs(safeQuote.checkin_date || (hiddenCheckinInput ? hiddenCheckinInput.value : ""));
        syncNightsInputs(nights);

        if (panelRoomAmountEl) panelRoomAmountEl.textContent = formatKrw(roomAmount);
        if (extraGuestsEl) extraGuestsEl.textContent = `${extraInfo.extraGuests}명`;
        if (panelExtraAmountEl) panelExtraAmountEl.textContent = formatKrw(extraInfo.extraAmount);
        if (panelBbqAmountEl) panelBbqAmountEl.textContent = formatKrw(extraInfo.bbqAmount);
        if (panelTotalAmountEl) panelTotalAmountEl.textContent = formatKrw(totalAmount);

        if (panelTotalGuestsEl) {
            const total = Number(safeQuote.total_guests || getGuestTotal());
            panelTotalGuestsEl.textContent = `${total}명`;
        }

        // 토스 결제위젯 금액 동기화 (초기화 또는 업데이트)
        initOrUpdateTossWidgets(totalAmount);
    };

    const fetchQuote = async () => {
        const checkinDate = hiddenCheckinInput ? hiddenCheckinInput.value : "";
        const nights = Number(hiddenNightsInput ? hiddenNightsInput.value : nightsSelect?.value || 1);

        if (!checkinDate) {
            setStatus("체크인 날짜를 선택해 주세요.", "error");
            return null;
        }

        const stayValidation = bookingCalendarController
            ? bookingCalendarController.validateStay({
                checkinDate,
                nights,
            })
            : { ok: true };

        if (!stayValidation.ok) {
            setStatus(stayValidation.message || "선택한 숙박 기간을 확인해 주세요.", "error");
            if (paySubmitBtn) paySubmitBtn.disabled = true;
            return null;
        }

        if (paySubmitBtn) paySubmitBtn.disabled = false;

        try {
            const response = await fetch(apiUrl("/api/payment/quote"), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    checkin_date: checkinDate,
                    nights,
                    adults: guestState.adults,
                    bbq: !!(bbqCheckbox && bbqCheckbox.checked),
                    pet_with: !!(petCheckbox && petCheckbox.checked),
                }),
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "요금 계산에 실패했습니다.");
            }

            applyQuote(data);
            setStatus("");
            return data;
        } catch (error) {
            setStatus(error.message || "요금 계산 중 오류가 발생했습니다.", "error");
            return null;
        }
    };

    const validateRequired = () => {
        const checkinDate = hiddenCheckinInput ? hiddenCheckinInput.value : "";
        if (!checkinDate) {
            setStatus("체크인 날짜를 선택해 주세요.", "error");
            if (checkinInput) checkinInput.focus();
            return false;
        }

        const nights = Number(nightsSelect ? nightsSelect.value : 1);
        const stayValidation = bookingCalendarController
            ? bookingCalendarController.validateStay({
                checkinDate,
                nights,
            })
            : { ok: true };
        if (!stayValidation.ok) {
            setStatus(stayValidation.message || "선택한 숙박 기간에 이미 예약된 날짜가 포함되어 있습니다.", "error");
            return false;
        }

        if (!customerNameInput || !customerNameInput.value.trim()) {
            setStatus("예약자명을 입력해 주세요.", "error");
            if (customerNameInput) customerNameInput.focus();
            return false;
        }

        const phoneDigits = normalizePhone(customerPhoneInput ? customerPhoneInput.value : "");
        if (!/^01[0-9]{8,9}$/.test(phoneDigits)) {
            setStatus("연락처 형식을 확인해 주세요. (예: 01012345678)", "error");
            if (customerPhoneInput) customerPhoneInput.focus();
            return false;
        }

        const total = getGuestTotal();
        if (total <= 0 || total > MAX_GUESTS) {
            setStatus(`총 인원은 1명 이상 ${MAX_GUESTS}명 이하로 선택해 주세요.`, "error");
            return false;
        }

        const allTermsChecked = requiredAgreeInputs.every((input) => input.checked);
        if (!allTermsChecked) {
            setStatus("필수 약관에 모두 동의해 주세요.", "error");
            return false;
        }

        return true;
    };

    const submitPayment = async () => {
        if (!validateRequired()) return;

        const quote = lastQuote || (await fetchQuote());
        if (!quote) return;

        const payload = {
            customer_name: customerNameInput ? customerNameInput.value.trim() : "",
            customer_phone: customerPhoneInput ? customerPhoneInput.value.trim() : "",
            checkin_date: hiddenCheckinInput ? hiddenCheckinInput.value : "",
            nights: Number(hiddenNightsInput ? hiddenNightsInput.value : 1),
            adults: guestState.adults,
            bbq: !!(bbqCheckbox && bbqCheckbox.checked),
            pet_with: !!(petCheckbox && petCheckbox.checked),
            agreed_to_terms: true,
            terms_version: TERMS_VERSION,
            agree_policy: !!(agreePolicyInput && agreePolicyInput.checked),
            agree_privacy: !!(agreePrivacyInput && agreePrivacyInput.checked),
            agree_thirdparty: !!(agreeThirdpartyInput && agreeThirdpartyInput.checked),
            agree_adult: !!(agreeAdultInput && agreeAdultInput.checked),
            arrival_time: arrivalTimeSelect ? arrivalTimeSelect.value : "",
            request_note: requestNoteInput ? requestNoteInput.value.trim() : "",
        };

        if (!tossWidgets) {
            setStatus("결제 위젯이 아직 준비되지 않았습니다. 잠시 후 다시 시도해 주세요.", "error");
            return;
        }

        if (paySubmitBtn) paySubmitBtn.disabled = true;
        setStatus("주문 정보를 생성하는 중입니다.");

        try {
            // 1. 백엔드에 주문 생성 요청 → order_id, amount 반환
            const response = await fetch(apiUrl("/api/payment/prepare"), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "주문 생성에 실패했습니다.");
            }

            setStatus("결제창을 여는 중입니다...", "success");

            // 2. 토스 결제위젯 결제 요청 (Redirect 방식)
            await tossWidgets.requestPayment({
                orderId: data.order_id,
                orderName: `물레방아하우스 숙박 예약 (${payload.nights}박)`,
                successUrl: window.location.origin + apiUrl("/reservation/success"),
                failUrl: window.location.origin + apiUrl("/reservation/fail"),
                customerName: payload.customer_name,
                customerMobilePhone: normalizePhone(payload.customer_phone),
            });

        } catch (error) {
            // 사용자가 결제창을 닫은 경우 등
            setStatus(error.message || "결제 준비 중 오류가 발생했습니다.", "error");
            if (paySubmitBtn) paySubmitBtn.disabled = false;
        }
    };

    const initDefaultValues = async () => {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const tomorrow = new Date(today);
        tomorrow.setDate(today.getDate() + 1);

        const minDate = toYmd(today);

        const queryCheckin = qs.get("checkin");
        const queryNights = Number(qs.get("nights") || 1);
        const parsedQueryDate = queryCheckin ? parseYmd(queryCheckin) : null;
        const preferredCheckin =
            parsedQueryDate && queryCheckin >= minDate ? queryCheckin : toYmd(tomorrow);

        const safeNights = Number.isFinite(queryNights) ? Math.min(5, Math.max(1, queryNights)) : 1;
        syncNightsInputs(safeNights);

        const adultsFromQuery = Number(qs.get("adults") || guestState.adults);

        guestState.adults = Math.max(GUEST_MINIMUM.adults, Number.isFinite(adultsFromQuery) ? adultsFromQuery : 2);

        adjustGuestWithinLimit();

        if (bbqCheckbox) bbqCheckbox.checked = parseBoolean(qs.get("bbq"));
        if (petCheckbox) petCheckbox.checked = parseBoolean(qs.get("pet")) || parseBoolean(qs.get("pet_with"));

        if (window.WatermillReservationCalendar?.createAvailabilityCalendar) {
            bookingCalendarController = window.WatermillReservationCalendar.createAvailabilityCalendar({
                calendarId: "booking-calendar",
                selectedDateId: "booking-calendar-selected-date",
                statusId: "booking-calendar-status",
                maxNights: 5,
                initialCheckin: preferredCheckin,
                initialNights: safeNights,
                autoCloseOnValidRange: true,
                onOpenChange: onCalendarOpenChange,
                onValidRangeSelect: ({ checkinDate, nights }) => {
                    syncCheckinInputs(checkinDate);
                    syncNightsInputs(nights);
                    setStatus("");
                    fetchQuote();
                },
            });

            const calendarReady = await bookingCalendarController.ready;
            if (calendarReady) {
                const initialStay = resolveInitialStay(preferredCheckin, safeNights);
                syncCheckinInputs(initialStay.checkinDate);
                syncNightsInputs(initialStay.nights);
                bookingCalendarController.setSelection(initialStay);
            } else {
                bookingCalendarController = null;
                setStatus("예약 달력을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.", "error");
                syncCheckinInputs(preferredCheckin);
            }
        } else {
            bookingCalendarController = null;
            setStatus("예약 달력 모듈을 찾을 수 없습니다.", "error");
            syncCheckinInputs(preferredCheckin);
        }

        syncGuestUi();
        syncOptionChecks();
    };

    const onGuestCountChanged = async (event) => {
        const input = event.currentTarget;
        const group = input.dataset.guestGroup;
        if (!group || !GUEST_GROUPS.includes(group)) return;

        const previous = guestState[group];
        const selectedValue = Number(input.value);

        // Keep one selection per group even with checkbox UI.
        if (!input.checked) {
            setGroupSelection(group, previous);
            return;
        }

        const nextTotal = getGuestTotal() - previous + selectedValue;
        if (nextTotal > MAX_GUESTS) {
            setStatus(`총 인원은 최대 ${MAX_GUESTS}명까지 가능합니다.`, "error");
            setGroupSelection(group, previous);
            return;
        }

        guestState[group] = Math.max(GUEST_MINIMUM[group], selectedValue);
        syncGuestUi();
        await fetchQuote();
    };

    if (agreeAllInput) {
        agreeAllInput.addEventListener("change", () => {
            requiredAgreeInputs.forEach((input) => {
                input.checked = agreeAllInput.checked;
            });
        });
    }

    requiredAgreeInputs.forEach((input) => {
        input.addEventListener("change", syncAgreeAll);
    });


    guestCountInputs.forEach((input) => {
        input.addEventListener("change", onGuestCountChanged);
    });

    [bbqCheckbox, petCheckbox].forEach((input) => {
        if (!input) return;
        input.addEventListener("change", async () => {
            syncOptionChecks();
            await fetchQuote();
        });
    });

    if (customerPhoneInput) {
        customerPhoneInput.addEventListener("input", () => {
            customerPhoneInput.value = formatPhone(customerPhoneInput.value);
        });
    }

    if (checkinInput) {
        checkinInput.addEventListener("click", () => {
            openBookingCalendar();
        });

        checkinInput.addEventListener("focus", () => {
            if (suppressCheckinFocusOpen) {
                suppressCheckinFocusOpen = false;
                return;
            }
            openBookingCalendar();
        });

        checkinInput.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                openBookingCalendar();
                return;
            }

            if (event.key === "Escape") {
                event.preventDefault();
                closeBookingCalendar(true);
            }
        });
    }

    if (bookingCalendarBackdrop) {
        bookingCalendarBackdrop.addEventListener("click", () => {
            closeBookingCalendar(true);
        });
    }

    if (bookingCalendarCloseBtn) {
        bookingCalendarCloseBtn.addEventListener("click", () => {
            closeBookingCalendar(true);
        });
    }

    if (nightsSelect) {
        nightsSelect.addEventListener("change", (e) => {
            const previousNights = Number(hiddenNightsInput ? hiddenNightsInput.value : 1);
            const nextNights = Number(e.target.value);
            const checkinDate = hiddenCheckinInput ? hiddenCheckinInput.value : "";

            if (!checkinDate) {
                syncNightsInputs(nextNights);
                return;
            }

            const stayValidation = bookingCalendarController
                ? bookingCalendarController.validateStay({
                    checkinDate,
                    nights: nextNights,
                })
                : { ok: true };

            if (!stayValidation.ok) {
                setStatus(stayValidation.message || "선택하신 숙박 기간을 확인해 주세요.", "error");
                syncNightsInputs(previousNights);
                syncCalendarSelection();
                return;
            }

            syncNightsInputs(nextNights);
            syncCalendarSelection();
            fetchQuote();
        });
    }

    if (paySubmitBtn) {
        paySubmitBtn.addEventListener("click", submitPayment);
    }

    termViewButtons.forEach((button) => {
        button.addEventListener("click", () => {
            openTermsModal(button.dataset.termKey || "");
        });
    });

    termsModalCloseTargets.forEach((target) => {
        target.addEventListener("click", closeTermsModal);
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeTermsModal();
            closeBookingCalendar(true);
        }
    });

    document.addEventListener("mousedown", (event) => {
        if (!bookingDateField || !bookingDateField.classList.contains("is-calendar-open")) return;
        if (bookingDateField.contains(event.target)) return;
        closeBookingCalendar(false);
    });

    initDefaultValues().then(() => {
        syncAgreeAll();
        fetchQuote();
    });
});
