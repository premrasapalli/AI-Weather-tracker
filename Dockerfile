# Use the official Python image as the base image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt .

# Install the required dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask app files into the container
COPY . .

# Expose the port that the app will run on
EXPOSE 8080

# Define the command to run your application
CMD ["python", "app.py"]
