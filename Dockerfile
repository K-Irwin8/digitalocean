FROM python:3.12-slim-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV XDG_CACHE_HOME=/app/.cache  


# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy only the necessary files
COPY requirements.txt .
COPY application.py .
COPY process_video.py .
COPY templates/ templates/
COPY static/ static/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the Whisper model during the build
RUN mkdir -p /app/.cache
RUN python -c "import whisper; whisper.load_model('small')"

#here
# Create a non-root user and group
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set the home directory for the new user
ENV HOME=/home/appuser
ENV USER=appuser

# Change ownership of the app directory
RUN chown -R appuser:appuser /app

# Switch to the new user
USER appuser

# Continue with the build steps
WORKDIR /app

# Install dependencies and pre-download the model as appuser
RUN python -c "import whisper; whisper.load_model('small')"

# to here
# Copy the rest of the application code
#COPY . .

# Create necessary directories
RUN mkdir -p uploads static/translated_videos

# Set environment variables for Flask
ENV FLASK_APP=application.py
ENV FLASK_RUN_HOST=0.0.0.0

# Command to run on container start (Shell Form for variable substitution)
CMD gunicorn application:app --bind 0.0.0.0:$PORT



