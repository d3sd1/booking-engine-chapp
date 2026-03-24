# Booking Engine — Solution Documentation

## Overview

This document describes all changes made to the booking engine project, covering both the **3 required tasks** from the technical test and the **extra improvements** added to demonstrate architecture and engineering maturity.

---

## Required Tasks (Standard)

### Task 1: Filter Room Panel

**Requirement:** Add a search form at the top of the Rooms section to filter rooms by name. The filter should search rooms whose `name` field contains the entered text (e.g., "Room 1" shows "Room 1.1", "Room 1.2" but not "Room 2.1").

**Implementation:**
- `pms/views.py` — `RoomsView.get()` accepts an optional `?q=` GET parameter and applies `name__icontains` filter on the queryset
- `pms/templates/rooms.html` — Added a search form with text input, submit button, and a "Clear" button that appears only when a filter is active. Shows a warning alert when no rooms match
- Method: GET-based for bookmarkable URLs and natural browser back-button behavior

**Why GET instead of POST:** GET is semantically correct for search operations — the request is idempotent, results can be bookmarked, and the browser history works naturally.

**Tests (branch `feature/filter-room-panel`):** 8 tests covering partial match, exact match, exclusion, case insensitivity, empty query, no results, and context preservation.

---

### Task 2: Occupancy Percentage Widget

**Requirement:** Add a new widget to the Dashboard showing "% ocupación", calculated as: confirmed bookings / total existing rooms.

**Implementation:**
- `pms/views.py` — `DashboardView.get()` calculates `occupancy_pct = (confirmed_bookings / total_rooms * 100)` with division-by-zero protection
- `pms/templates/dashboard.html` — New purple card widget (#8e44ad) aligned with existing design, using `floatformat:1` for one decimal place. Added `flex-wrap` for responsive layout
- Uses `Booking.objects.filter(state=Booking.NEW).count()` — the model constant `NEW` represents confirmed/active bookings (as defined in `Booking.STATE_CHOICES`)
- Cancelled bookings (`state=DEL`) are excluded from the count

**Tests (branch `feature/occupancy-widget`):** 5 tests covering zero occupancy, correct calculation (2/4 = 50%), exclusion of cancelled bookings, and template rendering.

---

### Task 3: Edit Booking Dates

**Requirement:** Add a link to each booking to edit its dates. The new page should have a form with only checkin/checkout fields and a "Save" button. Must validate room availability for the new dates and show "No hay disponibilidad para las fechas seleccionadas" if occupied.

**Implementation:**
- `pms/forms.py` — `EditBookingDatesForm` with checkin/checkout DateField inputs and checkout > checkin validation
- `pms/views.py` — `EditBookingDatesView` handles GET (pre-fills current dates) and POST (validates availability before saving)
- `pms/urls.py` — Route `booking/<pk>/edit-dates` registered as `edit_booking_dates`
- `pms/templates/edit_booking_dates.html` — Form showing booking details (code, room, customer), date inputs, error display, and Save/Back buttons
- `pms/templates/home.html` — "Editar fechas" link added next to "Editar datos de contacto", hidden for cancelled bookings
- Availability check uses `checkin__lt=new_checkout, checkout__gt=new_checkin` (standard interval overlap detection), excluding the booking being edited via `exclude(id=booking.id)` and excluding cancelled bookings via `state=Booking.NEW`
- Total price is automatically recalculated when dates change

**Why `exclude(id=booking.id)` matters:** Without this, extending a booking's own dates would falsely conflict with itself. This is a correctness edge case that most implementations miss.

**Tests (branch `feature/edit-booking-dates`):** 11 tests covering form rendering, successful edit, total recalculation, conflict detection, self-exclusion, cancelled booking exclusion, date order validation, link visibility, partial overlap, and adjacent booking (checkout=checkin is NOT a conflict).

---

## Extra Improvements (Beyond Requirements)

### Code Quality Refactoring

**Why:** The original codebase had several code smells that would be flagged in a code review. Fixing them demonstrates the ability to identify and improve existing code.

| Issue found | Fix applied |
|---|---|
| `from .forms import *` | Replaced with explicit imports (PEP 8) |
| `print(context)` in `RoomDetailsView` | Removed — debug statement leaked to stdout |
| `Room.objects.get(id=pk)` without 404 handling | Replaced with `get_object_or_404()` everywhere |
| Hardcoded `"NEW"`, `"DEL"` strings in queries | Replaced with `Booking.NEW`, `Booking.DELETED` model constants |
| `not "x" in y` syntax | Fixed to idiomatic `"x" not in y` (PEP 8 E713) |
| `from datetime import ...` inside method body | Moved to module-level imports |
| Duplicate comment `# get outcoming guests` above invoiced query | Fixed to `# get total invoiced today` |
| `guests` widget using `DateInput` instead of `NumberInput` | Fixed to `forms.NumberInput` |

### Service Layer (`pms/services.py`)

**Why:** Business logic was embedded directly in views, mixing HTTP concerns with domain rules. Extracting to a service layer makes the logic testable independently, reusable across views, and easier to reason about.

| Function | Purpose |
|---|---|
| `get_available_rooms(checkin, checkout, guests)` | Room search with date/guest filtering and price annotation |
| `is_room_available(room, checkin, checkout, exclude_booking_id)` | Single-room availability check with booking exclusion |
| `calculate_booking_total(room, checkin, checkout)` | Price calculation from room rate and stay duration |
| `_parse_date(value)` | Type coercion: accepts str, datetime, or date transparently |

### Server-Side Date Validation

**Why:** The original code only validated dates via HTML `min`/`max` attributes (client-side only). This was listed as a TODO in the original README. Client-side validation can be bypassed.

- `DateRangeValidationMixin` — Reusable mixin ensuring `checkout > checkin` and `checkin >= today`, shared between `RoomSearchForm` and `EditBookingDatesForm`
- Guest count validation (1-4) with `clean_guests()` method
- `is_room_available()` check added to `BookingView.post` before creating new bookings (also listed as a TODO in the original README)
- Error feedback via `django.contrib.messages` when availability check fails

### CI/CD Pipeline (GitHub Actions)

**Why:** Automated quality gates prevent regressions and enforce standards on every PR.

- `.github/workflows/ci.yml` — Runs on PRs and pushes to develop/main
- Python 3.10/3.11 matrix for compatibility testing
- flake8 linting with project-specific config (`setup.cfg`)
- Test coverage with 95% minimum threshold
- pip dependency caching for faster builds

### Jenkins Pipeline (Jenkinsfile)

**Why:** Enterprise CI/CD with Git Flow multi-environment strategy.

| Stage | What it does |
|---|---|
| Setup | Creates venv, installs dependencies |
| Lint | flake8 with pylint-format report |
| Test & Coverage | 95% threshold, XML reports |
| SonarQube Analysis | Static analysis with quality gate |
| Quality Gate | Blocks pipeline if SonarQube fails |
| Liquibase Migrations | Runs DB migrations with environment-appropriate context |
| Build Docker Image | Tagged with branch-buildnumber |
| Deploy | Per-branch: develop/staging/preprod/main (production requires manual approval) |

### Liquibase Database Migrations

**Why:** Database-agnostic schema management that works independently of the application ORM. Enables versioned, auditable DDL/DML changes.

| Changelog | Type | Content | Environments |
|---|---|---|---|
| `001-create-schema.xml` | DDL | 4 tables with FKs and constraints | All |
| `002-add-indexes.xml` | DDL | 6 performance indexes | All |
| `003-seed-room-data.xml` | DML | 4 room types + 25 rooms (per business spec) | All |
| `004-mock-data.xml` | DML | 4 customers + 6 bookings (test scenarios) | local, preprod only |

**Context strategy:**
- `local` — Full dataset including mocks for development
- `staging` — Schema + seed data, no mocks
- `preprod` — Schema + seed + mocks for realistic testing
- `production` — Schema + seed only, no test data

### Stateless Architecture for Multi-Node Scaling

**Why:** SQLite is file-based and cannot be shared across nodes. A stateless application allows horizontal scaling.

| Aspect | Implementation |
|---|---|
| Database | PostgreSQL via `DATABASE_URL` env var (falls back to SQLite for local dev) |
| Sessions | `SESSION_ENGINE = 'django.contrib.sessions.backends.db'` — stored in DB, not filesystem |
| Static files | Served via whitenoise (embedded, no external storage needed) |
| WSGI server | Gunicorn with 3 workers (production-ready, replaces Django dev server) |
| Docker | Non-root user (`appuser`), healthchecks on PostgreSQL |

### Environment-Aware Configuration

**Why:** Different environments need different security postures, logging levels, and behaviors.

| Setting | local | staging | preprod | production |
|---|---|---|---|---|
| DEBUG | True | False | False | False |
| Logging (pms) | DEBUG | INFO | DEBUG | INFO |
| Logging (django) | INFO | WARNING | WARNING | WARNING |
| Security headers | Off | On | On | On |
| Secure cookies | No | No | No | Yes |

### Project Configuration

| File | Purpose |
|---|---|
| `.env.example` | Environment variable template |
| `.dockerignore` | Keeps Docker build context clean |
| `setup.cfg` | flake8 configuration |
| `sonar-project.properties` | SonarQube project settings |
| `Dockerfile` | Python 3.11-slim, gunicorn, non-root user |
| `docker-compose.yml` | PostgreSQL + Liquibase + web app |

---

## Test Summary

| Test Class | Count | What it covers |
|---|---|---|
| ModelStrTests | 4 | `__str__` methods for all models |
| HomeViewTests | 2 | Home page loads, shows bookings |
| BookingSearchViewTests | 3 | Redirect without filter, search by code, search by name |
| RoomSearchViewTests | 2 | Form rendering, room availability search |
| BookingViewTests | 3 | Booking form, booking creation, 404 for invalid room |
| DeleteBookingViewTests | 2 | Confirmation page, cancellation |
| EditBookingViewTests | 2 | Edit form, customer update |
| EditBookingDatesTests | 10 | Date editing, conflicts, self-exclusion, adjacent bookings |
| DashboardTests | 5 | Load, zero occupancy, calculation, cancellation exclusion, widget rendering |
| RoomFilterTests | 4 | All rooms, partial filter, no results, case insensitive |
| RoomDetailsViewTests | 2 | Details page, 404 |
| ServiceLayerTests | 8 | Availability, pricing, room search, date parsing |
| FormValidationTests | 5 | Date order, past dates, guest range, reservation code |
| **Total** | **52** | **99% coverage** |

---

## Security Considerations

### Server-side total recalculation
`BookingView.post()` recalculates the booking total server-side via `calculate_booking_total()` instead of trusting the `total` hidden form field from the POST body. This prevents a classic price manipulation vulnerability where a user could submit `total=0` via browser devtools. The test `test_post_creates_booking` explicitly verifies this by sending `total=999` and asserting the server calculates `40.0`.

### TOCTOU window in room search
Between `RoomSearchView.post()` (shows available rooms) and `BookingView.post()` (creates the booking), another user could book the same room. This is a Time-Of-Check-Time-Of-Use (TOCTOU) race condition. It is mitigated by the `is_room_available()` check in `BookingView.post()` which re-validates availability at save time. The remaining window is acceptable for a single-server deployment. For high-concurrency production, `SELECT FOR UPDATE` or optimistic locking would be needed.

### URL type safety
All URL patterns use `<int:pk>` instead of `<str:pk>`. This prevents non-numeric IDs from reaching `get_object_or_404()` — the URL resolver rejects them with a clean 404 instead of a 500 server error.

## Known Technical Debt

| Item | Status | Notes |
|---|---|---|
| `Booking.total` uses `FloatField` | Documented as TODO | Should be `DecimalField(max_digits=10, decimal_places=2)` with `ROUND_HALF_UP` for PCI-DSS compliance and to avoid accumulated rounding errors (e.g., 0.01 differences in invoiced totals) |
| `Room_type` class name | Not changed | PEP 8 recommends `RoomType`, but changing requires migration and affects all FK references across the codebase |

---

## Git Branch Strategy

```
main (original codebase from oscarchapp/testbookingengine)
  └── develop
        ├── feature/filter-room-panel       (Task 1: 2 commits)
        ├── feature/occupancy-widget        (Task 2: 2 commits)
        ├── feature/edit-booking-dates      (Task 3: 2 commits)
        ├── feature/ci-cd                   (Extra: 1 commit)
        ├── feature/code-quality            (Extra: 5 commits)
        └── feature/enterprise-quality      (Extra: 6 commits)
```

Each feature branch targets `develop` via Pull Request. Commits follow conventional commit format (`feat:`, `refactor:`, `test:`, `ci:`, `fix:`, `chore:`, `infra:`).
