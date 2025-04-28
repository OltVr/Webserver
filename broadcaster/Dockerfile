# Simple Dockerfile for the Broadcaster service

# Use a slim Python image
FROM python:3.9-alpine

# Set working directory
WORKDIR /app

# Install necessary Python packages
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the broadcaster code
COPY broadcaster.py ./

# Command to run the broadcaster
CMD ["python3", "broadcaster.py"]
