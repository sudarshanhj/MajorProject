# Use a slim Python image
FROM python:3.10-slim

# Install system dependencies for OpenCV and PostgreSQL
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /code

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
# Ensure gunicorn is installed
RUN pip install --no-cache-dir gunicorn

# Copy the rest of the application
COPY . .

# Hugging Face Spaces runs on port 7860 by default
ENV PORT=7860
EXPOSE 7860

# Start the application
CMD ["gunicorn", "--timeout", "120", "-w", "1", "-b", "0.0.0.0:7860", "app:app"]
