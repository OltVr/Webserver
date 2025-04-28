# Use a lightweight Python image
FROM python:3.9-alpine

# Set the working directory inside the container
WORKDIR /usr/src/app

# Copy only necessary files
COPY . /usr/src/app/

# Install Flask with pip
RUN pip install --no-cache-dir flask requests

# Set the command to run the server
CMD ["python", "/usr/src/app/webserver.py"]
