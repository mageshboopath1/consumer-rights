FROM python:3.9-slim

WORKDIR /app

# Copy all files including security module
COPY . .

# Install dependencies
RUN pip install pika

# Create log directory for security logs
RUN mkdir -p /var/log/app && chmod 777 /var/log/app

CMD ["python", "piiFilter.py"]