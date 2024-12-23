# Use a lightweight Python image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install only necessary Python dependencies
RUN pip install --no-cache-dir requests schedule

# Copy the script into the container
COPY sync_script.py .

# Run as a non-root user for security
RUN useradd -m syncuser
USER syncuser

# Set the default command to execute the script
CMD ["python", "sync_script.py"]
