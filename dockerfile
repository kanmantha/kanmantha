# -----------------------------
# Stage 1: Base Image
# -----------------------------
FROM python:3.11-slim

# Prevent Python from writing pyc files and using buffered stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# -----------------------------
# Stage 2: Install dependencies
# -----------------------------
# Copy the dependency list first (for Docker caching)
COPY requirements.txt .

# Install system dependencies (optional but helpful)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------
# Stage 3: Copy application code
# -----------------------------
COPY . .

# Expose both Flask (5000) and Django (8000) ports
EXPOSE 5000 8000

# -----------------------------
# Stage 4: Start the application
# -----------------------------
# By default, your lms_single.py runs both Flask and Django in threads
CMD ["python", "lms_single.py"]
