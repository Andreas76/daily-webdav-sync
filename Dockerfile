# Use a lightweight Python image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install dependencies directly
RUN pip install --no-cache-dir requests schedule

# Copy the script
COPY sync_script.py .

# Set the default command to execute the script
CMD ["python", "sync_script.py"]
