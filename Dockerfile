
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

ENV PORT=3000

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} app:app"]
