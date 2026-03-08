(function () {
    function toYmd(date) {
        const normalized = normalizeDate(date);
        if (!normalized) return '';
        const year = normalized.getFullYear();
        const month = String(normalized.getMonth() + 1).padStart(2, '0');
        const day = String(normalized.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    function normalizeDate(value) {
        if (!value) return null;

        let date;
        if (value instanceof Date) {
            date = new Date(value);
        } else if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
            date = new Date(`${value}T00:00:00`);
        } else {
            date = new Date(value);
        }

        if (Number.isNaN(date.getTime())) {
            return null;
        }

        date.setHours(0, 0, 0, 0);
        return date;
    }

    function addDays(date, days) {
        const next = normalizeDate(date);
        if (!next) return null;
        next.setDate(next.getDate() + Number(days || 0));
        return next;
    }

    function formatDisplayDate(date) {
        return new Intl.DateTimeFormat('ko-KR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            weekday: 'short',
        }).format(date);
    }

    function diffNights(checkin, checkout) {
        const oneDayMs = 24 * 60 * 60 * 1000;
        return Math.round((checkout.getTime() - checkin.getTime()) / oneDayMs);
    }

    async function fetchJson(url) {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`요청 실패: ${response.status}`);
        }
        return response.json();
    }

    function getAppBasePath() {
        const path = window.location.pathname;
        const marker = '/reservation/';
        const markerIndex = path.indexOf(marker);
        if (markerIndex >= 0) {
            return path.slice(0, markerIndex);
        }
        if (path === '/') return '';
        return path.endsWith('/') ? path.slice(0, -1) : path;
    }

    function withAppBase(suffix) {
        return `${getAppBasePath()}${suffix}`;
    }

    function createUnavailableController(message) {
        const reason = message || '달력을 불러오지 못했습니다.';
        return {
            open() {},
            close() {},
            setSelection() {
                return { ok: false, message: reason };
            },
            validateStay() {
                return { ok: false, message: reason };
            },
            destroy() {},
            ready: Promise.resolve(false),
        };
    }

    function createAvailabilityCalendar(options) {
        const config = Object.assign(
            {
                calendarId: 'reservation-list-calendar',
                selectedDateId: 'reservation-list-selected-date',
                statusId: 'reservation-list-status',
                bookButtonId: 'reservation-list-book-btn',
                bookBaseUrl: withAppBase('/reservation/book/'),
                maxNights: 5,
                initialCheckin: '',
                initialNights: 1,
                autoCloseOnValidRange: false,
                onValidRangeSelect: null,
                onOpenChange: null,
            },
            options || {}
        );

        const calendarRoot = document.getElementById(config.calendarId);
        if (!calendarRoot || typeof flatpickr === 'undefined') {
            return createUnavailableController('달력을 사용할 수 없습니다.');
        }

        const selectedDateElement = config.selectedDateId
            ? document.getElementById(config.selectedDateId)
            : null;
        const statusElement = config.statusId ? document.getElementById(config.statusId) : null;
        const bookButton = config.bookButtonId ? document.getElementById(config.bookButtonId) : null;

        const bookingField = calendarRoot.closest('.booking-date-field');
        const popover = bookingField ? bookingField.querySelector('.booking-calendar-popover') : null;
        const backdrop = bookingField ? bookingField.querySelector('.booking-calendar-backdrop') : null;

        const today = normalizeDate(new Date());
        const rangeEnd = addDays(today, 540);
        const bookedDates = new Set();
        const holidayDates = new Set();

        let calendarInstance = null;
        let isReady = false;
        let destroyed = false;
        let isOpen = false;
        let suppressValidRangeCallback = false;
        let pendingSelection = config.initialCheckin
            ? {
                checkinDate: config.initialCheckin,
                nights: Number(config.initialNights || 1),
            }
            : null;

        const setStatus = (text, statusType) => {
            if (!statusElement) return;
            statusElement.textContent = text;
            statusElement.classList.remove('is-available', 'is-booked');
            if (statusType) {
                statusElement.classList.add(
                    statusType === 'available' ? 'is-available' : 'is-booked'
                );
            }
        };

        const setBookButton = (checkinDate, nights) => {
            if (!bookButton) return;

            if (!checkinDate || !nights || nights < 1) {
                bookButton.classList.add('is-disabled');
                bookButton.textContent = '객실 예약 페이지로 이동';
                bookButton.href = config.bookBaseUrl;
                return;
            }

            const url = new URL(config.bookBaseUrl, window.location.href);
            url.searchParams.set('checkin', toYmd(checkinDate));
            url.searchParams.set('nights', String(nights));
            url.searchParams.set('adults', '2');

            bookButton.classList.remove('is-disabled');
            bookButton.textContent = `${nights}박 일정으로 예약하기`;
            bookButton.href = `${url.pathname}${url.search}`;
        };

        const updateMonthHeading = (instance) => {
            const heading =
                instance && instance.calendarContainer
                    ? instance.calendarContainer.querySelector('.flatpickr-current-month')
                    : null;
            if (!heading) return;
            heading.dataset.label = `${instance.currentYear}년 ${instance.currentMonth + 1}월`;
        };

        const isBooked = (dateObj) => {
            const date = normalizeDate(dateObj);
            if (!date) return true;
            if (date < today) return true;
            return bookedDates.has(toYmd(date));
        };

        const hasBlockedNightInRange = (checkin, checkout) => {
            let cursor = normalizeDate(checkin);
            while (cursor && cursor < checkout) {
                if (isBooked(cursor)) return true;
                cursor = addDays(cursor, 1);
            }
            return false;
        };

        const validateStay = ({ checkinDate, nights }) => {
            if (!isReady) {
                return { ok: false, message: '예약 달력을 준비 중입니다. 잠시 후 다시 시도해 주세요.' };
            }

            const checkin = normalizeDate(checkinDate);
            const safeNights = Number(nights || 0);

            if (!checkin) {
                return { ok: false, message: '체크인 날짜를 선택해 주세요.' };
            }

            if (!Number.isFinite(safeNights) || safeNights < 1) {
                return { ok: false, message: '숙박일수는 1박 이상이어야 합니다.' };
            }

            if (safeNights > config.maxNights) {
                return {
                    ok: false,
                    message: `숙박일수는 최대 ${config.maxNights}박까지 선택할 수 있습니다.`,
                };
            }

            if (checkin < today) {
                return { ok: false, message: '오늘 이후 날짜만 선택할 수 있습니다.' };
            }

            const checkout = addDays(checkin, safeNights);
            if (!checkout) {
                return { ok: false, message: '체크아웃 날짜를 계산할 수 없습니다.' };
            }

            if (hasBlockedNightInRange(checkin, checkout)) {
                return {
                    ok: false,
                    message: '선택한 구간에 예약 마감일이 포함되어 있습니다. 다른 날짜를 선택해 주세요.',
                };
            }

            return {
                ok: true,
                message: '',
                checkin,
                checkout,
                nights: safeNights,
            };
        };

        const setOpenState = (nextOpen) => {
            isOpen = Boolean(nextOpen);
            if (bookingField) {
                bookingField.classList.toggle('is-calendar-open', isOpen);
            }
            if (popover) {
                popover.hidden = !isOpen;
            }
            if (backdrop) {
                backdrop.hidden = !isOpen;
            }
            if (typeof config.onOpenChange === 'function') {
                config.onOpenChange(isOpen);
            }
        };

        const updateSelectionUi = (selectedDates) => {
            if (!selectedDates || selectedDates.length === 0) {
                if (selectedDateElement) {
                    selectedDateElement.textContent = '선택 일정: 없음';
                }
                setStatus('체크인과 체크아웃을 선택하면 예약 가능 여부를 확인할 수 있습니다.');
                setBookButton(null, 0);
                return;
            }

            const checkin = normalizeDate(selectedDates[0]);
            if (!checkin) {
                if (selectedDateElement) {
                    selectedDateElement.textContent = '선택 일정: 없음';
                }
                setStatus('체크인 날짜를 선택해 주세요.', 'booked');
                setBookButton(null, 0);
                return;
            }

            if (selectedDates.length === 1) {
                if (selectedDateElement) {
                    selectedDateElement.textContent = `체크인: ${formatDisplayDate(checkin)} / 체크아웃: 선택 필요`;
                }
                setStatus('체크아웃 날짜를 선택해 주세요.', 'available');
                setBookButton(null, 0);
                return;
            }

            const checkout = normalizeDate(selectedDates[1]);
            if (!checkout) {
                if (selectedDateElement) {
                    selectedDateElement.textContent = `체크인: ${formatDisplayDate(checkin)} / 체크아웃: 선택 필요`;
                }
                setStatus('체크아웃 날짜를 선택해 주세요.', 'available');
                setBookButton(null, 0);
                return;
            }

            const nights = diffNights(checkin, checkout);
            const validation = validateStay({
                checkinDate: checkin,
                nights,
            });

            if (selectedDateElement) {
                selectedDateElement.textContent = `체크인: ${formatDisplayDate(checkin)} / 체크아웃: ${formatDisplayDate(checkout)}${validation.ok ? ` (${nights}박)` : ''}`;
            }

            if (!validation.ok) {
                setStatus(validation.message, 'booked');
                setBookButton(null, 0);
                return;
            }

            setStatus('선택한 일정은 예약 가능합니다. 일정이 예약 폼에 반영됩니다.', 'available');
            setBookButton(validation.checkin, validation.nights);

            if (!suppressValidRangeCallback && typeof config.onValidRangeSelect === 'function') {
                config.onValidRangeSelect({
                    checkinDate: toYmd(validation.checkin),
                    checkoutDate: toYmd(validation.checkout),
                    nights: validation.nights,
                });
            }

            if (!suppressValidRangeCallback && config.autoCloseOnValidRange) {
                controller.close();
            }
        };

        const controller = {
            open() {
                if (!popover) return;
                setOpenState(true);
                window.requestAnimationFrame(() => {
                    if (!calendarInstance) return;
                    calendarInstance.redraw();
                    updateMonthHeading(calendarInstance);
                });
            },
            close() {
                if (!popover) return;
                setOpenState(false);
            },
            setSelection(selection) {
                pendingSelection = selection || null;

                if (!isReady || !calendarInstance) {
                    return {
                        ok: false,
                        message: '예약 달력을 준비 중입니다. 잠시 후 다시 시도해 주세요.',
                    };
                }

                if (!selection || !selection.checkinDate) {
                    suppressValidRangeCallback = true;
                    calendarInstance.clear(false);
                    suppressValidRangeCallback = false;
                    updateSelectionUi([]);
                    return { ok: false, message: '체크인 날짜를 선택해 주세요.' };
                }

                const validation = validateStay({
                    checkinDate: selection.checkinDate,
                    nights: selection.nights,
                });

                if (!validation.ok) {
                    suppressValidRangeCallback = true;
                    calendarInstance.clear(false);
                    suppressValidRangeCallback = false;
                    updateSelectionUi([]);
                    setStatus(validation.message, 'booked');
                    setBookButton(null, 0);
                    return validation;
                }

                suppressValidRangeCallback = true;
                calendarInstance.setDate([validation.checkin, validation.checkout], false);
                suppressValidRangeCallback = false;
                updateSelectionUi([validation.checkin, validation.checkout]);
                return validation;
            },
            validateStay(params) {
                return validateStay(params);
            },
            destroy() {
                destroyed = true;
                if (calendarInstance) {
                    calendarInstance.destroy();
                    calendarInstance = null;
                }
                setOpenState(false);
            },
            ready: null,
        };

        controller.ready = (async () => {
            try {
                const [availability, calendarConfig] = await Promise.all([
                    fetchJson(
                        withAppBase(
                            `/api/calendar/availability?start=${toYmd(today)}&end=${toYmd(rangeEnd)}`
                        )
                    ).catch(() => ({ booked_dates: [] })),
                    fetchJson(withAppBase('/api/calendar/config')).catch(() => ({
                        holiday_dates: [],
                    })),
                ]);

                if (Array.isArray(availability.booked_dates)) {
                    availability.booked_dates.forEach((value) => {
                        if (typeof value === 'string' && value.trim()) {
                            bookedDates.add(value.trim());
                        }
                    });
                }

                if (Array.isArray(calendarConfig.holiday_dates)) {
                    calendarConfig.holiday_dates.forEach((value) => {
                        if (typeof value === 'string' && value.trim()) {
                            holidayDates.add(value.trim());
                        }
                    });
                }
            } catch (_error) {
                setStatus(
                    '예약 가능일 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.',
                    'booked'
                );
                setBookButton(null, 0);
                return false;
            }

            if (destroyed) return false;

            calendarInstance = flatpickr(calendarRoot, {
                inline: true,
                mode: 'range',
                locale: flatpickr.l10ns && flatpickr.l10ns.ko ? flatpickr.l10ns.ko : undefined,
                dateFormat: 'Y-m-d',
                monthSelectorType: 'static',
                disableMobile: true,
                minDate: 'today',
                showMonths: 1,
                disable: [(date) => isBooked(date)],
                onDayCreate: (_dObj, _dStr, _fp, dayElement) => {
                    if (
                        dayElement.classList.contains('prevMonthDay') ||
                        dayElement.classList.contains('nextMonthDay')
                    ) {
                        return;
                    }

                    const day = dayElement.dateObj.getDay();
                    if (day === 0) dayElement.classList.add('day-sunday');
                    if (day === 6) dayElement.classList.add('day-saturday');

                    const ymd = toYmd(dayElement.dateObj);
                    if (holidayDates.has(ymd)) {
                        dayElement.classList.add('day-holiday');
                    }

                    if (isBooked(dayElement.dateObj)) {
                        dayElement.classList.add('status-booked');
                    } else {
                        dayElement.classList.add('status-available');
                    }
                },
                onChange: (selectedDates) => {
                    updateSelectionUi(selectedDates);
                },
                onMonthChange: (_selectedDates, _dateStr, instance) => {
                    updateMonthHeading(instance);
                },
                onYearChange: (_selectedDates, _dateStr, instance) => {
                    updateMonthHeading(instance);
                },
                onReady: (_selectedDates, _dateStr, instance) => {
                    const shell = calendarRoot.closest('.reservation-calendar-shell');
                    if (shell) {
                        const mountedOutside = Array.from(shell.children).some(
                            (child) =>
                                child.classList &&
                                child.classList.contains('flatpickr-calendar') &&
                                child.classList.contains('inline')
                        );
                        if (mountedOutside) {
                            shell.classList.add('calendar-mounted-outside');
                        }
                    }

                    updateMonthHeading(instance);
                    updateSelectionUi([]);
                },
            });

            isReady = true;

            if (pendingSelection && pendingSelection.checkinDate) {
                controller.setSelection(pendingSelection);
            } else {
                updateSelectionUi([]);
            }

            return true;
        })();

        return controller;
    }

    function initAvailabilityCalendar(options) {
        return createAvailabilityCalendar(options);
    }

    window.WatermillReservationCalendar = {
        createAvailabilityCalendar,
        initAvailabilityCalendar,
    };
})();
