FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY overlay ./overlay
COPY fonts ./fonts
COPY weather_icons ./weather_icons

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["python", "overlay/flask_overlay_server.py"]
