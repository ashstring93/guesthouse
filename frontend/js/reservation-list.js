document.addEventListener('DOMContentLoaded', () => {
    if (!window.MullebangReservationCalendar) return;

    window.MullebangReservationCalendar.initAvailabilityCalendar({
        calendarId: 'reservation-list-calendar',
        selectedDateId: 'reservation-list-selected-date',
        statusId: 'reservation-list-status',
        bookButtonId: 'reservation-list-book-btn'
    });
});
