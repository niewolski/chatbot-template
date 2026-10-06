FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY app.py .
COPY bot/ ./bot/

EXPOSE 5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "-w", "1", "--timeout", "120", "app:app"]
