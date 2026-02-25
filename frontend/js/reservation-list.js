document.addEventListener('DOMContentLoaded', () => {
    if (!window.WatermillReservationCalendar) return;

    window.WatermillReservationCalendar.initAvailabilityCalendar({
        calendarId: 'reservation-list-calendar',
        selectedDateId: 'reservation-list-selected-date',
        statusId: 'reservation-list-status',
        bookButtonId: 'reservation-list-book-btn'
    });
});
