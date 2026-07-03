FROM python:3.11-slim

# Install the stress utility
RUN apt-get update && apt-get install -y stress-ng && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .

CMD ["python", "app.py"]