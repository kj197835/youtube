FROM python:3.11-slim

WORKDIR /app

# Install git for the automation script (push to github)
RUN apt-get update && apt-get install -y git tzdata && rm -rf /var/lib/apt/lists/*
ENV TZ=Asia/Seoul

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port for OAuth callback
EXPOSE 8080

CMD ["python", "fetch_data.py"]
