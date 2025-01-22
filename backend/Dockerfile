FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
# Command to run the app using Gunicorn with Eventlet (optional for WebSocket support)
CMD ["gunicorn", "--worker-class", "eventlet", "--bind", "0.0.0.0:5000", "app:app"]