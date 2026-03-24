from datetime import date, timedelta

from django.test import TestCase, Client
from django.urls import reverse

from .models import Room, Room_type, Booking, Customer


class EditBookingDatesTests(TestCase):
    """Tests for the booking dates editing functionality."""

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
