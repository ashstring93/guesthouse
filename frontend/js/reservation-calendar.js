(function () {
    function toYmd(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    function normalizeDate(value) {
        const date = new Date(value);
        date.setHours(0, 0, 0, 0);
        return date;
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

    async function initAvailabilityCalendar(options) {
        const config = Object.assign(
            {
                calendarId: 'reservation-list-calendar',
                selectedDateId: 'reservation-list-selected-date',
                statusId: 'reservation-list-status',
                bookButtonId: 'reservation-list-book-btn',
                bookBaseUrl: '/reservation/book',
                maxNights: 5,
            },
            options || {}
        );

        const calendarRoot = document.getElementById(config.calendarId);
        if (!calendarRoot || typeof flatpickr === 'undefined') return;

        const selectedDateElement = document.getElementById(config.selectedDateId);
        const statusElement = document.getElementById(config.statusId);
        const bookButton = document.getElementById(config.bookButtonId);

        const today = normalizeDate(new Date());
        const rangeEnd = normalizeDate(new Date(today));
        rangeEnd.setDate(rangeEnd.getDate() + 540);

        const bookedDates = new Set();

        const setStatus = (text, statusType) => {
            if (!statusElement) return;
            statusElement.textContent = text;
            statusElement.classList.remove('is-available', 'is-booked');
            if (statusType) {
                statusElement.classList.add(statusType === 'available' ? 'is-available' : 'is-booked');
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

            const url = new URL(config.bookBaseUrl, window.location.origin);
            url.searchParams.set('checkin', toYmd(checkinDate));
            url.searchParams.set('nights', String(nights));
            url.searchParams.set('adults', '2');

            bookButton.classList.remove('is-disabled');
            bookButton.textContent = `${nights}박 일정으로 예약하기`;
            bookButton.href = `${url.pathname}${url.search}`;
        };

        const updateMonthHeading = (instance) => {
            const heading = instance && instance.calendarContainer
                ? instance.calendarContainer.querySelector('.flatpickr-current-month')
                : null;
            if (!heading) return;
            heading.dataset.label = `${instance.currentYear}년 ${instance.currentMonth + 1}월`;
        };

        const isBooked = (dateObj) => {
            const date = normalizeDate(dateObj);
            if (date < today) return true;
            return bookedDates.has(toYmd(date));
        };

        const hasBlockedNightInRange = (checkin, checkout) => {
            const cursor = new Date(checkin);
            while (cursor < checkout) {
                if (isBooked(cursor)) return true;
                cursor.setDate(cursor.getDate() + 1);
            }
            return false;
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

            if (selectedDates.length === 1) {
                if (selectedDateElement) {
                    selectedDateElement.textContent = `체크인: ${formatDisplayDate(checkin)} / 체크아웃: 선택 필요`;
                }
                setStatus('체크아웃 날짜를 선택해 주세요.', 'available');
                setBookButton(null, 0);
                return;
            }

            const checkout = normalizeDate(selectedDates[1]);
            const nights = diffNights(checkin, checkout);

            if (nights < 1) {
                if (selectedDateElement) {
                    selectedDateElement.textContent = '선택 일정: 없음';
                }
                setStatus('체크아웃 날짜는 체크인 다음 날부터 선택할 수 있습니다.', 'booked');
                setBookButton(null, 0);
                return;
            }

            if (nights > config.maxNights) {
                if (selectedDateElement) {
                    selectedDateElement.textContent = `체크인: ${formatDisplayDate(checkin)} / 체크아웃: ${formatDisplayDate(checkout)}`;
                }
                setStatus(`숙박일수는 최대 ${config.maxNights}박까지 선택할 수 있습니다.`, 'booked');
                setBookButton(null, 0);
                return;
            }

            if (hasBlockedNightInRange(checkin, checkout)) {
                if (selectedDateElement) {
                    selectedDateElement.textContent = `체크인: ${formatDisplayDate(checkin)} / 체크아웃: ${formatDisplayDate(checkout)}`;
                }
                setStatus('선택한 구간에 예약 마감일이 포함되어 있습니다. 다른 날짜를 선택해 주세요.', 'booked');
                setBookButton(null, 0);
                return;
            }

            if (selectedDateElement) {
                selectedDateElement.textContent = `체크인: ${formatDisplayDate(checkin)} / 체크아웃: ${formatDisplayDate(checkout)} (${nights}박)`;
            }
            setStatus('선택한 일정은 예약 가능합니다. 아래 버튼으로 예약을 진행해 주세요.', 'available');
            setBookButton(checkin, nights);
        };

        try {
            const availability = await fetchJson(
                `/api/calendar/availability?start=${toYmd(today)}&end=${toYmd(rangeEnd)}`
            );

            if (Array.isArray(availability.booked_dates)) {
                availability.booked_dates.forEach((value) => {
                    if (typeof value === 'string' && value.trim()) {
                        bookedDates.add(value.trim());
                    }
                });
            }
        } catch (_error) {
            setStatus('예약 가능일 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.', 'booked');
            setBookButton(null, 0);
            return;
        }

        flatpickr(calendarRoot, {
            inline: true,
            mode: 'range',
            locale: flatpickr.l10ns && flatpickr.l10ns.ko ? flatpickr.l10ns.ko : undefined,
            dateFormat: 'Y-m-d',
            monthSelectorType: 'static',
            disableMobile: true,
            minDate: 'today',
            showMonths: 1,
            disable: [
                (date) => isBooked(date),
            ],
            onDayCreate: (_dObj, _dStr, _fp, dayElement) => {
                if (dayElement.classList.contains('prevMonthDay') || dayElement.classList.contains('nextMonthDay')) {
                    return;
                }

                const day = dayElement.dateObj.getDay();
                if (day === 0) dayElement.classList.add('day-sunday');
                if (day === 6) dayElement.classList.add('day-saturday');

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
                    const mountedOutside = Array.from(shell.children).some((child) =>
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
    }

    window.MullebangReservationCalendar = {
        initAvailabilityCalendar,
    };
})();
