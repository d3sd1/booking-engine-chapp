from datetime import datetime

from django.db.models import F, Count

from .models import Booking, Room


def _parse_date(value):
    """Convert a string date (YYYY-MM-DD) or datetime to a date object."""
    if isinstance(value, str):
        return datetime.strptime(value, "%Y-%m-%d").date()
    if isinstance(value, datetime):
        return value.date()
    return value


def get_available_rooms(checkin, checkout, guests):
    """
    Return available rooms and their totals for the given date range and guest count.

    Accepts date objects or 'YYYY-MM-DD' strings.
    Returns a tuple of (rooms_queryset, room_type_summary_queryset, total_days).
    """
    checkin = _parse_date(checkin)
    checkout = _parse_date(checkout)
    total_days = (checkout - checkin).days

    filters = {
        'room_type__max_guests__gte': guests,
    }
    exclude = {
        'booking__checkin__lt': checkout,
        'booking__checkout__gt': checkin,
        'booking__state__exact': Booking.NEW,
    }

    rooms = (Room.objects
             .filter(**filters)
             .exclude(**exclude)
             .annotate(total=total_days * F('room_type__price'))
             .order_by("room_type__max_guests", "name"))

    summary = (Room.objects
               .filter(**filters)
               .exclude(**exclude)
               .values("room_type__name", "room_type")
               .annotate(total=Count('room_type'))
               .order_by("room_type__max_guests"))

    return rooms, summary, total_days


def is_room_available(room, checkin, checkout, exclude_booking_id=None):
    """
    Check if a room is available for the given date range.

    Optionally excludes a booking (useful when editing an existing booking's dates).
    Only considers confirmed (NEW) bookings as conflicting.
    """
    checkin = _parse_date(checkin)
    checkout = _parse_date(checkout)
    conflicting = Booking.objects.filter(
        room=room,
        state=Booking.NEW,
        checkin__lt=checkout,
        checkout__gt=checkin,
    )
    if exclude_booking_id:
        conflicting = conflicting.exclude(id=exclude_booking_id)
    return not conflicting.exists()


def calculate_booking_total(room, checkin, checkout):
    """Calculate the total price for a booking based on room price and stay duration."""
    checkin = _parse_date(checkin)
    checkout = _parse_date(checkout)
    total_days = (checkout - checkin).days
    return total_days * room.room_type.price
