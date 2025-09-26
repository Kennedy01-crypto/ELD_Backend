web: gunicorn eld_backend.wsgi:application --bind 0.0.0.0:$PORT
worker: celery -A eld_backend worker --loglevel=info
beat: celery -A eld_backend beat --loglevel=info
