from datetime import date, timedelta

from django.test import TestCase, Client
from django.urls import reverse

from .models import Room, Room_type, Booking, Customer


class EditBookingDatesTests(TestCase):
    """Tests for the booking dates editing functionality."""
class DashboardOccupancyTests(TestCase):
    """Tests for the occupancy percentage widget on the dashboard."""
from django.test import TestCase, Client
from django.urls import reverse

from .models import Room, Room_type


class RoomFilterTests(TestCase):
    """Tests for the room name filter functionality."""

    @classmethod
    def setUpTestData(cls):
        single = Room_type.objects.create(name='Individual', price=20, max_guests=1)
        cls.room = Room.objects.create(name='Room 1.1', description='Single', room_type=single)
        cls.customer = Customer.objects.create(name='Test User', email='test@test.com', phone='123456789')

    def setUp(self):
        self.client = Client()
        self.tomorrow = date.today() + timedelta(days=1)
        self.in_3_days = date.today() + timedelta(days=3)
        self.in_5_days = date.today() + timedelta(days=5)
        self.in_7_days = date.today() + timedelta(days=7)

        self.booking = Booking.objects.create(
            checkin=self.tomorrow, checkout=self.in_3_days, room=self.room,
            guests=1, customer=self.customer, total=40, code='TEST0001', state=Booking.NEW,
        )

    def test_get_renders_form(self):
        response = self.client.get(reverse('edit_booking_dates', args=[self.booking.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Editar fechas de la reserva')
        self.assertContains(response, 'TEST0001')

    def test_successful_date_edit(self):
        response = self.client.post(
            reverse('edit_booking_dates', args=[self.booking.id]),
            {'checkin': self.in_5_days.isoformat(), 'checkout': self.in_7_days.isoformat()},
        )
        self.assertRedirects(response, '/')
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.checkin, self.in_5_days)
        self.assertEqual(self.booking.checkout, self.in_7_days)

    def test_recalculates_total_on_date_change(self):
        new_checkin = date.today() + timedelta(days=10)
        new_checkout = date.today() + timedelta(days=15)  # 5 days * 20€/day = 100€
        self.client.post(
            reverse('edit_booking_dates', args=[self.booking.id]),
            {'checkin': new_checkin.isoformat(), 'checkout': new_checkout.isoformat()},
        )
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.total, 100.0)

    def test_conflict_shows_error(self):
        Booking.objects.create(
            checkin=self.in_5_days, checkout=self.in_7_days, room=self.room,
            guests=1, customer=self.customer, total=40, code='TEST0002', state=Booking.NEW,
        )
        response = self.client.post(
            reverse('edit_booking_dates', args=[self.booking.id]),
            {'checkin': self.in_5_days.isoformat(), 'checkout': self.in_7_days.isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No hay disponibilidad para las fechas seleccionadas')

    def test_no_conflict_with_self(self):
        """Extending own booking dates should not conflict with itself."""
        new_checkout = self.in_3_days + timedelta(days=2)
        response = self.client.post(
            reverse('edit_booking_dates', args=[self.booking.id]),
            {'checkin': self.tomorrow.isoformat(), 'checkout': new_checkout.isoformat()},
        )
        self.assertRedirects(response, '/')

    def test_no_conflict_with_cancelled_booking(self):
        Booking.objects.create(
            checkin=self.in_5_days, checkout=self.in_7_days, room=self.room,
            guests=1, customer=self.customer, total=40, code='TEST0003', state=Booking.DELETED,
        )
        response = self.client.post(
            reverse('edit_booking_dates', args=[self.booking.id]),
            {'checkin': self.in_5_days.isoformat(), 'checkout': self.in_7_days.isoformat()},
        )
        self.assertRedirects(response, '/')

    def test_checkout_before_checkin_rejected(self):
        response = self.client.post(
            reverse('edit_booking_dates', args=[self.booking.id]),
            {'checkin': self.in_5_days.isoformat(), 'checkout': self.tomorrow.isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'La fecha de salida debe ser posterior')

    def test_edit_dates_link_visible_on_home(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Editar fechas')

    def test_edit_dates_link_hidden_for_cancelled(self):
        self.booking.state = Booking.DELETED
        self.booking.save()
        response = self.client.get(reverse('home'))
        self.assertNotContains(response, reverse('edit_booking_dates', args=[self.booking.id]))

    def test_partial_overlap_detected_as_conflict(self):
        Booking.objects.create(
            checkin=self.in_5_days, checkout=self.in_7_days, room=self.room,
            guests=1, customer=self.customer, total=40, code='TEST0004', state=Booking.NEW,
        )
        in_4_days = date.today() + timedelta(days=4)
        in_6_days = date.today() + timedelta(days=6)
        response = self.client.post(
            reverse('edit_booking_dates', args=[self.booking.id]),
            {'checkin': in_4_days.isoformat(), 'checkout': in_6_days.isoformat()},
        )
        self.assertContains(response, 'No hay disponibilidad para las fechas seleccionadas')

    def test_adjacent_booking_no_conflict(self):
        """checkout=day7 of other booking, our checkin=day7 should NOT conflict."""
        Booking.objects.create(
            checkin=self.in_5_days, checkout=self.in_7_days, room=self.room,
            guests=1, customer=self.customer, total=40, code='TEST0005', state=Booking.NEW,
        )
        in_9_days = date.today() + timedelta(days=9)
        response = self.client.post(
            reverse('edit_booking_dates', args=[self.booking.id]),
            {'checkin': self.in_7_days.isoformat(), 'checkout': in_9_days.isoformat()},
        )
        self.assertRedirects(response, '/')
        double = Room_type.objects.create(name='Doble', price=30, max_guests=2)

        cls.room_1 = Room.objects.create(name='Room 1.1', description='Single', room_type=single)
        cls.room_2 = Room.objects.create(name='Room 2.1', description='Double', room_type=double)
        cls.room_3 = Room.objects.create(name='Room 1.2', description='Single', room_type=single)
        cls.room_4 = Room.objects.create(name='Room 1.3', description='Single', room_type=single)

        cls.customer = Customer.objects.create(name='Test User', email='test@test.com', phone='123456789')
        triple = Room_type.objects.create(name='Triple', price=40, max_guests=3)

        Room.objects.create(name='Room 1.1', description='Single', room_type=single)
        Room.objects.create(name='Room 1.2', description='Single', room_type=single)
        Room.objects.create(name='Room 2.1', description='Double', room_type=double)
        Room.objects.create(name='Room 3.1', description='Triple', room_type=triple)

    def setUp(self):
        self.client = Client()

    def test_dashboard_loads(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_zero_occupancy_when_no_bookings(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['dashboard']['occupancy_pct'], 0)

    def test_occupancy_calculation(self):
        tomorrow = date.today() + timedelta(days=1)
        after = date.today() + timedelta(days=3)
        Booking.objects.create(
            checkin=tomorrow, checkout=after, room=self.room_1,
            guests=1, customer=self.customer, total=40, code='OCC00001', state=Booking.NEW,
        )
        Booking.objects.create(
            checkin=tomorrow, checkout=after, room=self.room_2,
            guests=2, customer=self.customer, total=60, code='OCC00002', state=Booking.NEW,
        )
        response = self.client.get(reverse('dashboard'))
        # 2 confirmed / 4 rooms = 50%
        self.assertEqual(response.context['dashboard']['occupancy_pct'], 50.0)

    def test_occupancy_excludes_cancelled_bookings(self):
        tomorrow = date.today() + timedelta(days=1)
        after = date.today() + timedelta(days=3)
        Booking.objects.create(
            checkin=tomorrow, checkout=after, room=self.room_1,
            guests=1, customer=self.customer, total=40, code='OCC00003', state=Booking.NEW,
        )
        Booking.objects.create(
            checkin=tomorrow, checkout=after, room=self.room_2,
            guests=2, customer=self.customer, total=60, code='OCC00004', state=Booking.DELETED,
        )
        response = self.client.get(reverse('dashboard'))
        # Only 1 confirmed / 4 rooms = 25%
        self.assertEqual(response.context['dashboard']['occupancy_pct'], 25.0)

    def test_occupancy_widget_renders_in_template(self):
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, '% Ocupación')
        self.assertContains(response, '0.0%')
    def test_rooms_list_shows_all_rooms(self):
        response = self.client.get(reverse('rooms'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['rooms']), 4)

    def test_filter_by_partial_name(self):
        response = self.client.get(reverse('rooms'), {'q': 'Room 1'})
        rooms = response.context['rooms']
        self.assertEqual(len(rooms), 2)
        names = [r['name'] for r in rooms]
        self.assertIn('Room 1.1', names)
        self.assertIn('Room 1.2', names)

    def test_filter_excludes_non_matching(self):
        response = self.client.get(reverse('rooms'), {'q': 'Room 1'})
        names = [r['name'] for r in response.context['rooms']]
        self.assertNotIn('Room 2.1', names)

    def test_filter_by_exact_name(self):
        response = self.client.get(reverse('rooms'), {'q': 'Room 2.1'})
        rooms = response.context['rooms']
        self.assertEqual(len(rooms), 1)
        self.assertEqual(rooms[0]['name'], 'Room 2.1')

    def test_filter_no_results(self):
        response = self.client.get(reverse('rooms'), {'q': 'NonExistent'})
        self.assertEqual(len(response.context['rooms']), 0)
        self.assertContains(response, 'No se encontraron habitaciones')

    def test_filter_case_insensitive(self):
        response = self.client.get(reverse('rooms'), {'q': 'room 1'})
        self.assertEqual(len(response.context['rooms']), 2)

    def test_empty_query_returns_all(self):
        response = self.client.get(reverse('rooms'), {'q': ''})
        self.assertEqual(len(response.context['rooms']), 4)

    def test_search_query_preserved_in_context(self):
        response = self.client.get(reverse('rooms'), {'q': 'Room 3'})
        self.assertEqual(response.context['search_query'], 'Room 3')
