FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=chapp.settings

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000
