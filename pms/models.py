from django.core.validators import RegexValidator
from django.db import models


phone_validator = RegexValidator(
    regex=r'^\+?[\d\s\-]{7,20}$',
    message='Formato de teléfono no válido. Ejemplo: +34 612 345 678'
)


class Customer(models.Model):
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=50, validators=[phone_validator])

    def __str__(self):
        return self.name


class Room_type(models.Model):
    name = models.CharField(max_length=100)
    price = models.FloatField()
    max_guests = models.IntegerField()

    def __str__(self):
        return self.name


class Room(models.Model):
    room_type = models.ForeignKey(Room_type, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=500)

    def __str__(self):
        return self.name


class Booking(models.Model):
    NEW = 'NEW'
    DELETED = 'DEL'
    STATE_CHOICES = [
        (NEW, 'Nueva'),
        (DELETED, 'Cancelada'),
    ]
    state = models.CharField(
        max_length=3,
        choices=STATE_CHOICES,
        default=NEW,
    )
    checkin = models.DateField()
    checkout = models.DateField()
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True)
    guests = models.IntegerField()
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True)
    total = models.FloatField()  # TODO: migrate to DecimalField to avoid floating-point rounding errors in pricing
    code = models.CharField(max_length=8)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code
