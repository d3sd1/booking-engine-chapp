from datetime import date, timedelta

from django.test import TestCase, Client
from django.urls import reverse

from .models import Room, Room_type, Booking, Customer


class BaseTestCase(TestCase):
    """Base test case that sets up common fixtures for the booking engine."""

    @classmethod
    def setUpTestData(cls):
        cls.single = Room_type.objects.create(name='Individual', price=20, max_guests=1)
        cls.double = Room_type.objects.create(name='Doble', price=30, max_guests=2)
        cls.triple = Room_type.objects.create(name='Triple', price=40, max_guests=3)
        cls.quad = Room_type.objects.create(name='Cuádruple', price=50, max_guests=4)

        cls.room_1_1 = Room.objects.create(name='Room 1.1', description='Single room', room_type=cls.single)
        cls.room_1_2 = Room.objects.create(name='Room 1.2', description='Single room', room_type=cls.single)
        cls.room_2_1 = Room.objects.create(name='Room 2.1', description='Double room', room_type=cls.double)
        cls.room_3_1 = Room.objects.create(name='Room 3.1', description='Triple room', room_type=cls.triple)

        cls.customer = Customer.objects.create(name='Test User', email='test@test.com', phone='123456789')

    def setUp(self):
        self.client = Client()


class ServerSideDateValidationTests(BaseTestCase):
    """Tests for server-side date validation on forms."""

    def test_search_form_validates_date_order(self):
        from .forms import RoomSearchForm
        form = RoomSearchForm(data={
            'checkin': (date.today() + timedelta(days=5)).isoformat(),
            'checkout': (date.today() + timedelta(days=2)).isoformat(),
            'guests': 1,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('La fecha de salida debe ser posterior', str(form.errors))

    def test_search_form_validates_past_checkin(self):
        from .forms import RoomSearchForm
        yesterday = date.today() - timedelta(days=1)
        form = RoomSearchForm(data={
            'checkin': yesterday.isoformat(),
            'checkout': (date.today() + timedelta(days=2)).isoformat(),
            'guests': 1,
        })
        self.assertFalse(form.is_valid())
        self.assertIn('La fecha de entrada no puede ser anterior a hoy', str(form.errors))

    def test_search_form_validates_guests_range(self):
        from .forms import RoomSearchForm
        form = RoomSearchForm(data={
            'checkin': (date.today() + timedelta(days=1)).isoformat(),
            'checkout': (date.today() + timedelta(days=3)).isoformat(),
            'guests': 5,
        })
        self.assertFalse(form.is_valid())

    def test_edit_dates_form_validates_date_order(self):
        from .forms import EditBookingDatesForm
        form = EditBookingDatesForm(data={
            'checkin': (date.today() + timedelta(days=5)).isoformat(),
            'checkout': (date.today() + timedelta(days=2)).isoformat(),
        })
        self.assertFalse(form.is_valid())
        self.assertIn('La fecha de salida debe ser posterior', str(form.errors))


class ServiceLayerTests(BaseTestCase):
    """Tests for the service layer functions."""

    def test_is_room_available_empty_room(self):
        from .services import is_room_available
        tomorrow = date.today() + timedelta(days=1)
        in_3_days = date.today() + timedelta(days=3)
        self.assertTrue(is_room_available(self.room_1_1, tomorrow, in_3_days))

    def test_is_room_available_with_conflict(self):
        from .services import is_room_available
        tomorrow = date.today() + timedelta(days=1)
        in_3_days = date.today() + timedelta(days=3)
        Booking.objects.create(
            checkin=tomorrow, checkout=in_3_days, room=self.room_1_1,
            guests=1, customer=self.customer, total=40, code='SVC00001', state=Booking.NEW,
        )
        self.assertFalse(is_room_available(self.room_1_1, tomorrow, in_3_days))

    def test_is_room_available_exclude_self(self):
        from .services import is_room_available
        tomorrow = date.today() + timedelta(days=1)
        in_3_days = date.today() + timedelta(days=3)
        booking = Booking.objects.create(
            checkin=tomorrow, checkout=in_3_days, room=self.room_1_1,
            guests=1, customer=self.customer, total=40, code='SVC00002', state=Booking.NEW,
        )
        self.assertTrue(is_room_available(self.room_1_1, tomorrow, in_3_days, exclude_booking_id=booking.id))

    def test_calculate_booking_total(self):
        from .services import calculate_booking_total
        tomorrow = date.today() + timedelta(days=1)
        in_6_days = date.today() + timedelta(days=6)
        total = calculate_booking_total(self.room_1_1, tomorrow, in_6_days)
        self.assertEqual(total, 100.0)

    def test_calculate_booking_total_with_strings(self):
        from .services import calculate_booking_total
        total = calculate_booking_total(
            self.room_2_1,
            (date.today() + timedelta(days=1)).isoformat(),
            (date.today() + timedelta(days=4)).isoformat(),
        )
        self.assertEqual(total, 90.0)

    def test_get_available_rooms_filters_by_guests(self):
        from .services import get_available_rooms
        tomorrow = date.today() + timedelta(days=1)
        in_3_days = date.today() + timedelta(days=3)
        rooms, _, _ = get_available_rooms(tomorrow, in_3_days, guests=3)
        room_names = [r.name for r in rooms]
        self.assertNotIn('Room 1.1', room_names)
        self.assertNotIn('Room 2.1', room_names)
        self.assertIn('Room 3.1', room_names)
