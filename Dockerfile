# Use a lightweight Python base image
FROM python:3.10-slim

# Install necessary Python libraries
RUN pip install webdavclient3 schedule

# Set the working directory inside the container
WORKDIR /app

# Copy the syncing script to the container
COPY sync_script.py .

# Run the syncing script
CMD ["python", "sync_script.py"]
