# psql_worker/Dockerfile
# Use a slim Python image for a smaller footprint
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY worker.py .

# Command to run the worker script
CMD ["python", "worker.py"]