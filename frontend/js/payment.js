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
    const hiddenChildrenInput = document.getElementById("booking-children");
    const hiddenInfantsInput = document.getElementById("booking-infants");

    const checkinInput = document.getElementById("booking-checkin");
    const nightsSelect = document.getElementById("booking-nights-visible");
    const arrivalTimeSelect = document.getElementById("arrival-time");
    const requestNoteInput = document.getElementById("request-note");

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

    const methodInputs = Array.from(document.querySelectorAll('input[name="payment_method"]'));

    const MAX_GUESTS = 6;
    const TERMS_VERSION = "2026-02-24-v1";
    const GUEST_GROUPS = ["adults", "children", "infants"];
    const BASE_GUESTS = 2;
    const ADULT_EXTRA_FEE = 20000;
    const CHILD_EXTRA_FEE = 10000;
    const INFANT_EXTRA_FEE = 5000;
    const BBQ_FEE = 20000;
    const GUEST_MINIMUM = {
        adults: 1,
        children: 0,
        infants: 0,
    };

    const qs = new URLSearchParams(window.location.search);

    const guestState = {
        adults: 2,
        children: 0,
        infants: 0,
    };

    let lastQuote = null;

    const TERM_DETAILS = {
        policy: {
            title: "유의사항/환불규정 동의",
            version: TERMS_VERSION,
            effectiveDate: "2026-02-24",
            lines: [
                "체크인 15:00 이후, 체크아웃 오전 11:00입니다.",
                "체크인 7일 전까지 취소 시 100% 환불됩니다.",
                "체크인 6일~3일 전 취소 시 50% 환불, 2일 이내 취소는 환불이 어렵습니다.",
                "천재지변 및 불가항력 상황은 별도 환불 정책이 적용될 수 있습니다.",
                "숙소 비품 훼손/분실 시 실제 비용이 청구될 수 있습니다.",
            ],
        },
        privacy: {
            title: "개인정보 수집 및 이용동의",
            version: TERMS_VERSION,
            effectiveDate: "2026-02-24",
            lines: [
                "수집 항목: 예약자명, 연락처, 체크인 정보, 결제 관련 확인정보.",
                "수집 목적: 예약 확인, 결제 처리, 고객 문의 대응.",
                "보유 기간: 관계 법령에서 정한 기간까지 보관 후 파기.",
                "동의 거부 시 예약 진행이 제한될 수 있습니다.",
            ],
        },
        thirdparty: {
            title: "개인정보 제3자 제공동의",
            version: TERMS_VERSION,
            effectiveDate: "2026-02-24",
            lines: [
                "제공 대상: 결제대행사(PG), 간편결제 사업자.",
                "제공 항목: 예약자명, 연락처, 주문번호, 결제금액.",
                "제공 목적: 결제 승인/정산, 환불 처리, 부정거래 방지.",
                "보유 기간: 관련 법령 및 계약에서 정한 기간.",
            ],
        },
        adult: {
            title: "미성년자 아님 동의",
            version: TERMS_VERSION,
            effectiveDate: "2026-02-24",
            lines: [
                "예약자는 미성년자가 아니며 본인 명의로 예약/결제를 진행합니다.",
                "미성년자 단독 예약이 확인될 경우 예약이 취소될 수 있습니다.",
                "허위 정보 입력으로 발생한 문제의 책임은 예약자에게 있습니다.",
            ],
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

    const formatKrw = (amount) => `${Number(amount || 0).toLocaleString("ko-KR")}원`;

    const setStatus = (text, type = "") => {
        if (!statusMessageEl) return;
        statusMessageEl.textContent = text || "";
        statusMessageEl.classList.remove("error", "success");
        if (type) {
            statusMessageEl.classList.add(type);
        }
    };

    const formatPhone = (value) => {
        const digits = String(value || "").replace(/[^0-9]/g, "").slice(0, 11);
        if (digits.length < 4) return digits;
        if (digits.length < 8) return `${digits.slice(0, 3)}-${digits.slice(3)}`;
        return `${digits.slice(0, 3)}-${digits.slice(3, 7)}-${digits.slice(7)}`;
    };

    const normalizePhone = (value) => String(value || "").replace(/[^0-9]/g, "");

    const parseBoolean = (value) => ["1", "true", "yes", "on"].includes(String(value || "").toLowerCase());

    const getGuestTotal = () => guestState.adults + guestState.children + guestState.infants;

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

    const syncMethodCards = () => {
        methodInputs.forEach((input) => {
            const card = input.closest(".method-item");
            if (!card) return;
            card.classList.toggle("active", input.checked);
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
        termsModalMeta.textContent = `약관 버전 ${detail.version} | 시행일 ${detail.effectiveDate}`;
        termsModalBody.innerHTML = detail.lines
            .map((line, index) => `<p>${index + 1}. ${escapeHtml(line)}</p>`)
            .join("");

        termsModal.hidden = false;
        document.body.classList.add("modal-open");
    };

    const syncAgreeAll = () => {
        if (!agreeAllInput) return;
        agreeAllInput.checked = requiredAgreeInputs.every((input) => input.checked);
    };

    const syncGuestUi = () => {
        if (hiddenAdultsInput) hiddenAdultsInput.value = String(guestState.adults);
        if (hiddenChildrenInput) hiddenChildrenInput.value = String(guestState.children);
        if (hiddenInfantsInput) hiddenInfantsInput.value = String(guestState.infants);

        GUEST_GROUPS.forEach((group) => {
            setGroupSelection(group, guestState[group]);
        });

        const total = getGuestTotal();
        if (guestTotalLabel) guestTotalLabel.textContent = `총 ${total}인 / 최대 ${MAX_GUESTS}인`;
        if (panelTotalGuestsEl) panelTotalGuestsEl.textContent = `${total}명`;
    };

    const adjustGuestWithinLimit = () => {
        while (getGuestTotal() > MAX_GUESTS) {
            if (guestState.infants > GUEST_MINIMUM.infants) {
                guestState.infants -= 1;
                continue;
            }
            if (guestState.children > GUEST_MINIMUM.children) {
                guestState.children -= 1;
                continue;
            }
            if (guestState.adults > GUEST_MINIMUM.adults) {
                guestState.adults -= 1;
                continue;
            }
            break;
        }
    };

    const calculateExtraByGroup = (nights, adults, children, infants, feeMeta = {}) => {
        const safeNights = Math.max(1, Number(nights || 1));
        let remainingFree = BASE_GUESTS;

        const freeAdults = Math.min(adults, remainingFree);
        remainingFree -= freeAdults;
        const freeChildren = Math.min(children, remainingFree);
        remainingFree -= freeChildren;
        const freeInfants = Math.min(infants, remainingFree);
        remainingFree -= freeInfants;

        const chargedAdults = Math.max(0, adults - freeAdults);
        const chargedChildren = Math.max(0, children - freeChildren);
        const chargedInfants = Math.max(0, infants - freeInfants);

        const adultFee = Number.isFinite(Number(feeMeta.adult_extra_fee))
            ? Number(feeMeta.adult_extra_fee)
            : ADULT_EXTRA_FEE;
        const childFee = Number.isFinite(Number(feeMeta.child_extra_fee))
            ? Number(feeMeta.child_extra_fee)
            : CHILD_EXTRA_FEE;
        const infantFee = Number.isFinite(Number(feeMeta.infant_extra_fee))
            ? Number(feeMeta.infant_extra_fee)
            : INFANT_EXTRA_FEE;
        const bbqFee = Number.isFinite(Number(feeMeta.bbq_fee))
            ? Number(feeMeta.bbq_fee)
            : BBQ_FEE;

        const extraAmount =
            (chargedAdults * adultFee + chargedChildren * childFee + chargedInfants * infantFee) * safeNights;
        const bbqAmount = bbqCheckbox && bbqCheckbox.checked ? bbqFee : 0;

        return {
            chargedAdults,
            chargedChildren,
            chargedInfants,
            extraGuests: chargedAdults + chargedChildren + chargedInfants,
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
            guestState.children,
            guestState.infants,
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

        if (hiddenCheckinInput) hiddenCheckinInput.value = safeQuote.checkin_date || "";
        if (hiddenNightsInput) hiddenNightsInput.value = String(nights);

        if (panelRoomAmountEl) panelRoomAmountEl.textContent = formatKrw(roomAmount);
        if (extraGuestsEl) extraGuestsEl.textContent = `${extraInfo.extraGuests}명`;
        if (panelExtraAmountEl) panelExtraAmountEl.textContent = formatKrw(extraInfo.extraAmount);
        if (panelBbqAmountEl) panelBbqAmountEl.textContent = formatKrw(extraInfo.bbqAmount);
        if (panelTotalAmountEl) panelTotalAmountEl.textContent = formatKrw(totalAmount);

        if (panelTotalGuestsEl) {
            const total = Number(safeQuote.total_guests || getGuestTotal());
            panelTotalGuestsEl.textContent = `${total}명`;
        }
    };

    const fetchQuote = async () => {
        const checkinDate = checkinInput ? checkinInput.value : "";
        const nights = Number(nightsSelect ? nightsSelect.value : 1);

        if (!checkinDate) {
            setStatus("체크인 날짜를 선택해 주세요.", "error");
            return null;
        }

        try {
            const response = await fetch(new URL("../api/payment/quote", window.location.href), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    checkin_date: checkinDate,
                    nights,
                    adults: guestState.adults,
                    children: guestState.children,
                    infants: guestState.infants,
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
        if (!checkinInput || !checkinInput.value) {
            setStatus("체크인 날짜를 선택해 주세요.", "error");
            if (checkinInput) checkinInput.focus();
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

        const checkedMethod = document.querySelector('input[name="payment_method"]:checked');
        const paymentMethod = checkedMethod ? checkedMethod.value : "card";

        const payload = {
            customer_name: customerNameInput ? customerNameInput.value.trim() : "",
            customer_phone: customerPhoneInput ? customerPhoneInput.value.trim() : "",
            checkin_date: hiddenCheckinInput ? hiddenCheckinInput.value : "",
            nights: Number(hiddenNightsInput ? hiddenNightsInput.value : 1),
            adults: guestState.adults,
            children: guestState.children,
            infants: guestState.infants,
            bbq: !!(bbqCheckbox && bbqCheckbox.checked),
            pet_with: !!(petCheckbox && petCheckbox.checked),
            payment_method: paymentMethod,
            agreed_to_terms: true,
            terms_version: TERMS_VERSION,
            agree_policy: !!(agreePolicyInput && agreePolicyInput.checked),
            agree_privacy: !!(agreePrivacyInput && agreePrivacyInput.checked),
            agree_thirdparty: !!(agreeThirdpartyInput && agreeThirdpartyInput.checked),
            agree_adult: !!(agreeAdultInput && agreeAdultInput.checked),
            arrival_time: arrivalTimeSelect ? arrivalTimeSelect.value : "",
            request_note: requestNoteInput ? requestNoteInput.value.trim() : "",
        };

        if (paySubmitBtn) paySubmitBtn.disabled = true;
        setStatus("주문 정보를 생성하는 중입니다.");

        try {
            const response = await fetch(new URL("../api/payment/prepare", window.location.href), {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "주문 생성에 실패했습니다.");
            }

            if (data.checkout_url) {
                setStatus("결제 페이지로 이동합니다.", "success");
                window.location.href = data.checkout_url;
                return;
            }

            setStatus(`${data.message} 주문번호: ${data.order_id}`, "success");
        } catch (error) {
            setStatus(error.message || "결제 준비 중 오류가 발생했습니다.", "error");
        } finally {
            if (paySubmitBtn) paySubmitBtn.disabled = false;
        }
    };

    const initDefaultValues = () => {
        const today = new Date();
        const tomorrow = new Date(today);
        tomorrow.setDate(today.getDate() + 1);

        const minDate = toYmd(today);
        if (checkinInput) checkinInput.min = minDate;

        const queryCheckin = qs.get("checkin");
        const queryNights = Number(qs.get("nights") || 1);
        const parsedQueryDate = queryCheckin ? parseYmd(queryCheckin) : null;
        const selectedDate =
            parsedQueryDate && queryCheckin >= minDate ? queryCheckin : toYmd(tomorrow);

        if (checkinInput) checkinInput.value = selectedDate;

        const safeNights = Number.isFinite(queryNights) ? Math.min(5, Math.max(1, queryNights)) : 1;
        if (nightsSelect) nightsSelect.value = String(safeNights);

        const adultsFromQuery = Number(qs.get("adults") || guestState.adults);
        const childrenFromQuery = Number(qs.get("children") || guestState.children);
        const infantsFromQuery = Number(qs.get("infants") || guestState.infants);

        guestState.adults = Math.max(GUEST_MINIMUM.adults, Number.isFinite(adultsFromQuery) ? adultsFromQuery : 2);
        guestState.children = Math.max(GUEST_MINIMUM.children, Number.isFinite(childrenFromQuery) ? childrenFromQuery : 0);
        guestState.infants = Math.max(GUEST_MINIMUM.infants, Number.isFinite(infantsFromQuery) ? infantsFromQuery : 0);

        adjustGuestWithinLimit();

        if (bbqCheckbox) bbqCheckbox.checked = parseBoolean(qs.get("bbq"));
        if (petCheckbox) petCheckbox.checked = parseBoolean(qs.get("pet")) || parseBoolean(qs.get("pet_with"));

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

    if (termsVersionLabel) {
        termsVersionLabel.textContent = `약관 버전: ${TERMS_VERSION}`;
    }

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

    methodInputs.forEach((input) => {
        input.addEventListener("change", syncMethodCards);
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

    [checkinInput, nightsSelect].forEach((input) => {
        if (!input) return;
        input.addEventListener("change", fetchQuote);
    });

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
        }
    });

    initDefaultValues();
    syncAgreeAll();
    syncMethodCards();
    fetchQuote();
});
