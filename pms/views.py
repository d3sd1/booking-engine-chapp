from datetime import date, datetime, time

from django.contrib import messages
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie

from .form_dates import Ymd
from .forms import *
from .models import Booking, Room
from .reservation_code import generate
from .services import calculate_booking_total, get_available_rooms, is_room_available


class BookingSearchView(View):
    # renders search results for bookingings
    def get(self, request):
        query = request.GET.dict()
        if "filter" not in query:
            return redirect("/")
        bookings = (Booking.objects
                    .filter(Q(code__icontains=query['filter']) | Q(customer__name__icontains=query['filter']))
                    .order_by("-created"))
        room_search_form = RoomSearchForm()
        context = {
            'bookings': bookings,
            'form': room_search_form,
            'filter': True
        }
        return render(request, "home.html", context)


class RoomSearchView(View):
    # renders the search form
    def get(self, request):
        room_search_form = RoomSearchForm()
        context = {
            'form': room_search_form
        }

        return render(request, "booking_search_form.html", context)

    # renders the search results of available rooms by date and guests
    def post(self, request):
        query = request.POST.dict()
        rooms, total_rooms, total_days = get_available_rooms(
            checkin=query['checkin'],
            checkout=query['checkout'],
            guests=query['guests'],
        )
        url_query = request.POST.urlencode()
        context = {
            "rooms": rooms,
            "total_rooms": total_rooms,
            "query": query,
            "url_query": url_query,
            "data": {"total_days": total_days},
        }
        return render(request, "search.html", context)


class HomeView(View):
    # renders home page with all the bookingings order by date of creation
    def get(self, request):
        bookings = Booking.objects.all().order_by("-created")
        context = {
            'bookings': bookings
        }
        return render(request, "home.html", context)


class BookingView(View):
    @method_decorator(ensure_csrf_cookie)
    def post(self, request, pk):
        customer_form = CustomerForm(request.POST, prefix="customer")
        if customer_form.is_valid():
            # Verify room availability before saving
            room = get_object_or_404(Room, id=pk)
            checkin = request.POST.get('booking-checkin')
            checkout = request.POST.get('booking-checkout')
            if not is_room_available(room, checkin, checkout):
                messages.error(request, 'No hay disponibilidad para las fechas seleccionadas.')
                return redirect('/')

            customer = customer_form.save()
            temp_POST = request.POST.copy()
            temp_POST.update({
                'booking-customer': customer.id,
                'booking-room': pk,
                'booking-code': generate.get()})
            booking_form = BookingForm(temp_POST, prefix="booking")
            if booking_form.is_valid():
                booking_form.save()
        return redirect('/')

    def get(self, request, pk):
        query = request.GET.dict()
        room = get_object_or_404(Room, id=pk)
        query['total'] = calculate_booking_total(room, query['checkin'], query['checkout'])
        url_query = request.GET.urlencode()
        booking_form = BookingFormExcluded(prefix="booking", initial=query)
        customer_form = CustomerForm(prefix="customer")
        context = {
            "url_query": url_query,
            "room": room,
            "booking_form": booking_form,
            "customer_form": customer_form
        }
        return render(request, "booking.html", context)


class DeleteBookingView(View):
    # renders the booking deletion form
    def get(self, request, pk):
        booking = get_object_or_404(Booking, id=pk)
        context = {
            'booking': booking
        }
        return render(request, "delete_booking.html", context)

    # deletes the booking
    def post(self, request, pk):
        Booking.objects.filter(id=pk).update(state=Booking.DELETED)
        return redirect("/")


class EditBookingView(View):
    # renders the booking edition form
    def get(self, request, pk):
        booking = get_object_or_404(Booking, id=pk)
        booking_form = BookingForm(prefix="booking", instance=booking)
        customer_form = CustomerForm(prefix="customer", instance=booking.customer)
        context = {
            'booking_form': booking_form,
            'customer_form': customer_form

        }
        return render(request, "edit_booking.html", context)

    # updates the customer form
    @method_decorator(ensure_csrf_cookie)
    def post(self, request, pk):
        booking = get_object_or_404(Booking, id=pk)
        customer_form = CustomerForm(request.POST, prefix="customer", instance=booking.customer)
        if customer_form.is_valid():
            customer_form.save()
            return redirect("/")


class EditBookingDatesView(View):
    def get(self, request, pk):
        booking = Booking.objects.get(id=pk)
        form = EditBookingDatesForm(initial={
            'checkin': booking.checkin,
            'checkout': booking.checkout,
        })
        context = {
            'booking': booking,
            'form': form,
        }
        return render(request, "edit_booking_dates.html", context)

    @method_decorator(ensure_csrf_cookie)
    def post(self, request, pk):
        booking = Booking.objects.get(id=pk)
        form = EditBookingDatesForm(request.POST)
        if form.is_valid():
            new_checkin = form.cleaned_data['checkin']
            new_checkout = form.cleaned_data['checkout']
            # Check room availability excluding the current booking
            conflicting = Booking.objects.filter(
                room=booking.room,
                state=Booking.NEW,
                checkin__lt=new_checkout,
                checkout__gt=new_checkin,
            ).exclude(id=booking.id)
            if conflicting.exists():
                form.add_error(None, 'No hay disponibilidad para las fechas seleccionadas.')
            else:
                total_days = (new_checkout - new_checkin).days
                booking.checkin = new_checkin
                booking.checkout = new_checkout
                booking.total = total_days * booking.room.room_type.price
                booking.save()
                return redirect('/')
        context = {
            'booking': booking,
            'form': form,
        }
        return render(request, "edit_booking_dates.html", context)


class DashboardView(View):
    def get(self, request):
        today = date.today()

        # get bookings created today
        today_min = datetime.combine(today, time.min)
        today_max = datetime.combine(today, time.max)
        today_range = (today_min, today_max)
        new_bookings = (Booking.objects
                        .filter(created__range=today_range)
                        .values("id")
                        ).count()

        # get incoming guests
        incoming = (Booking.objects
                    .filter(checkin=today)
                    .exclude(state=Booking.DELETED)
                    .values("id")
                    ).count()

        # get outcoming guests
        outcoming = (Booking.objects
                     .filter(checkout=today)
                     .exclude(state=Booking.DELETED)
                     .values("id")
                     ).count()

        # get total invoiced today
        invoiced = (Booking.objects
                    .filter(created__range=today_range)
                    .exclude(state=Booking.DELETED)
                    .aggregate(Sum('total'))
                    )

        # Calculate occupancy: confirmed bookings (state=NEW) / total rooms
        total_rooms = Room.objects.count()
        confirmed_bookings = Booking.objects.filter(state=Booking.NEW).count()
        occupancy_pct = (confirmed_bookings / total_rooms * 100) if total_rooms > 0 else 0

        # preparing context data
        dashboard = {
            'new_bookings': new_bookings,
            'incoming_guests': incoming,
            'outcoming_guests': outcoming,
            'invoiced': invoiced,
            'occupancy_pct': occupancy_pct,
        }

        context = {
            'dashboard': dashboard
        }
        return render(request, "dashboard.html", context)


class RoomDetailsView(View):
    def get(self, request, pk):
        # renders room details
        room = get_object_or_404(Room, id=pk)
        bookings = room.booking_set.all()
        context = {
            'room': room,
            'bookings': bookings,
        }
        return render(request, "room_detail.html", context)


class RoomsView(View):
    def get(self, request):
        query = request.GET.get('q', '').strip()
        rooms = Room.objects.all()
        if query:
            rooms = rooms.filter(name__icontains=query)
        rooms = rooms.values("name", "room_type__name", "id")
        context = {
            'rooms': rooms,
            'search_query': query,
        }
        return render(request, "rooms.html", context)
