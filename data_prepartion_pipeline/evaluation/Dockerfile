# Use an official lightweight Python image as a parent image
FROM python:3.10-slim

# Set the working directory inside the container to /app
WORKDIR /app

# Copy the requirements file into the container
# This is done first to leverage Docker's caching mechanism.
# The dependencies will only be re-installed if this file changes.
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's source code into the container
COPY . .

# Expose port 5001 to the outside world
EXPOSE 5001

# Define the command to run your app using gunicorn
# This command will be executed automatically when the container starts.
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "app:app"]