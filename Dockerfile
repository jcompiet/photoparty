# Use a lightweight Python base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Gunicorn
RUN pip install gunicorn

# Copy application code
COPY . .

# Command to run Gunicorn with Flask app
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
