from datetime import date, datetime
from django import forms
from django.forms import ModelForm, ValidationError

from .models import Booking, Customer

MAX_GUESTS = 4


class DateRangeValidationMixin:
    """Mixin that validates checkin < checkout and checkin >= today."""

    def clean(self):
        cleaned_data = super().clean()
        checkin = cleaned_data.get('checkin')
        checkout = cleaned_data.get('checkout')
        if checkin and checkout:
            if checkout <= checkin:
                raise ValidationError('La fecha de salida debe ser posterior a la fecha de entrada.')
            if checkin < date.today():
                raise ValidationError('La fecha de entrada no puede ser anterior a hoy.')
        return cleaned_data


class RoomSearchForm(DateRangeValidationMixin, forms.Form):
    """Search form for room availability. Uses forms.Form (not ModelForm)
    because this form drives a search query, not a model create/update."""
    checkin = forms.DateField(
        label='Checkin',
        widget=forms.DateInput(attrs={'type': 'date', 'min': datetime.today().strftime('%Y-%m-%d')}),
    )
    checkout = forms.DateField(
        label='Checkout',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'max': datetime.today().replace(month=12, day=31).strftime('%Y-%m-%d'),
        }),
    )
    guests = forms.IntegerField(
        label='Huéspedes',
        widget=forms.NumberInput(attrs={'min': 1, 'max': MAX_GUESTS}),
    )

    def clean_guests(self):
        guests = self.cleaned_data.get('guests')
        if guests is not None and (guests < 1 or guests > MAX_GUESTS):
            raise ValidationError(f'El número de huéspedes debe estar entre 1 y {MAX_GUESTS}.')
        return guests


class DateRangeValidationMixin:
    """Mixin that validates checkin < checkout and checkin >= today."""

    def clean(self):
        cleaned_data = super().clean()
        checkin = cleaned_data.get('checkin')
        checkout = cleaned_data.get('checkout')
        if checkin and checkout:
            if checkout <= checkin:
                raise ValidationError('La fecha de salida debe ser posterior a la fecha de entrada.')
            if checkin < date.today():
                raise ValidationError('La fecha de entrada no puede ser anterior a hoy.')
        return cleaned_data


class RoomSearchForm(DateRangeValidationMixin, ModelForm):
    class Meta:
        model = Booking
        fields = ['checkin', 'checkout', 'guests']
        labels = {
            "guests": "Huéspedes"
        }
        widgets = {
            'checkin': forms.DateInput(attrs={'type': 'date', 'min': datetime.today().strftime('%Y-%m-%d')}),
            'checkout': forms.DateInput(
                attrs={'type': 'date', 'max': datetime.today().replace(month=12, day=31).strftime('%Y-%m-%d')}),
            'guests': forms.NumberInput(attrs={'min': 1, 'max': MAX_GUESTS}),
        }

    def clean_guests(self):
        guests = self.cleaned_data.get('guests')
        if guests is not None and (guests < 1 or guests > MAX_GUESTS):
            raise ValidationError(f'El número de huéspedes debe estar entre 1 y {MAX_GUESTS}.')
        return guests


class CustomerForm(ModelForm):
    class Meta:
        model = Customer
        fields = "__all__"
        labels = {
            "name": "Nombre y apellido",
            "phone": "Teléfono"
        }


class BookingForm(ModelForm):
    class Meta:
        model = Booking
        fields = "__all__"
        labels = {}
        widgets = {
            'checkin': forms.HiddenInput(),
            'checkout': forms.HiddenInput(),
            'guests': forms.HiddenInput()
        }


class BookingFormExcluded(ModelForm):
    class Meta:
        model = Booking
        exclude = ["customer", "room", "code"]
        labels = {}
        widgets = {
            'checkin': forms.HiddenInput(),
            'checkout': forms.HiddenInput(),
            'guests': forms.HiddenInput(),
            'total': forms.HiddenInput(),
            'state': forms.HiddenInput(),
        }



class EditBookingDatesForm(DateRangeValidationMixin, forms.Form):
    checkin = forms.DateField(
        label='Fecha de entrada',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    checkout = forms.DateField(
        label='Fecha de salida',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        checkin = cleaned_data.get('checkin')
        checkout = cleaned_data.get('checkout')
        if checkin and checkout and checkout <= checkin:
            raise ValidationError('La fecha de salida debe ser posterior a la fecha de entrada.')
        return cleaned_data
