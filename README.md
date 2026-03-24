
# PMS

A small open-source PMS app made with Django.


## Stored data
- Type of rooms: name, n° of guests and price per day
- Rooms: name, description
- Customers: name, email, phone
- Bookings: checkin, checkout, total guests, customer information, total amount


## Features
- Create, delete and check bookings for each room
- Check room availability
- Find bookings by code or customer name
- Dashboard with bookings, incoming and outcoming customers, total invoiced and occupancy percentage
- Get detailed information about each room
- Edit customer information
- Edit booking dates with availability validation
- Filter rooms by name
- Server-side date validation (checkin >= today, checkout > checkin)
- Availability check before saving new bookings
- Service layer for business logic (availability, pricing)
- CI pipeline with tests, lint and coverage

## Local Deployment

To deploy this project locally run


### Using Docker
```bash
    docker compose up --build
```

### Using Virtualenv

```bash
    pip install virtualenv
    virtualenv pms
    source pms/bin/activate
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py runserver
```

### Django admin (/admin)
Use for username and password for superuser is "admin" (without quotes). Remember to change it.

### Warnings
- SECRET_KEY should be stored in .env file for production!
- DEBUG is set to TRUE.

## TODO List / Improvements

- Handle and create error pages
- Change date or define date range in dashboard


## License
[![MIT License](https://img.shields.io/apm/l/atomic-design-ui.svg?)](https://choosealicense.com/licenses/mit/)
