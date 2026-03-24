from django.test import TestCase, Client
from django.urls import reverse

from .models import Room, Room_type


class RoomFilterTests(TestCase):
    """Tests for the room name filter functionality."""

    @classmethod
    def setUpTestData(cls):
        single = Room_type.objects.create(name='Individual', price=20, max_guests=1)
        double = Room_type.objects.create(name='Doble', price=30, max_guests=2)
        triple = Room_type.objects.create(name='Triple', price=40, max_guests=3)

        Room.objects.create(name='Room 1.1', description='Single', room_type=single)
        Room.objects.create(name='Room 1.2', description='Single', room_type=single)
        Room.objects.create(name='Room 2.1', description='Double', room_type=double)
        Room.objects.create(name='Room 3.1', description='Triple', room_type=triple)

    def setUp(self):
        self.client = Client()

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
