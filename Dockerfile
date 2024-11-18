FROM python:3.12-slim-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV XDG_CACHE_HOME=/app/.cache  
ENV FFMPEG_BINARY=/bin/ffmpeg
ENV PATH="/bin:${PATH}"

# Install necessary system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    imagemagick \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    libpulse0 \
    xz-utils \
    && rm -rf /var/lib/apt/lists/* && \
    which ffmpeg && ffmpeg -version || echo "FFmpeg installation failed"

# Download and install FFmpeg static binary
RUN wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
    && tar -xvf ffmpeg-release-amd64-static.tar.xz \
    && mv ffmpeg-*-amd64-static/ffmpeg /bin/ \
    && mv ffmpeg-*-amd64-static/ffprobe /bin/ \
    && chmod +x /bin/ffmpeg /bin/ffprobe \
    && rm -rf ffmpeg-*-amd64-static ffmpeg-release-amd64-static.tar.xz

RUN which ffmpeg && ffmpeg -version || echo "FFmpeg not found"
RUN find / -type f -name ffmpeg || echo "FFmpeg binary not found"

# Backup the original policy.xml (if it exists)
RUN cp /etc/ImageMagick-6/policy.xml /etc/ImageMagick-6/policy.xml.bak || echo "No original file to back up"

# Replace policy.xml with a controlled version
RUN echo '<?xml version="1.0" encoding="UTF-8"?> \
<!DOCTYPE policymap SYSTEM "http://www.imagemagick.org/script/policy.xml"> \
<policymap> \
<policy domain="path" rights="read|write" pattern="@*" /> \
</policymap>' > /etc/ImageMagick-6/policy.xml

# Debugging: Confirm the content of policy.xml
RUN echo "Debugging policy.xml content:" && cat /etc/ImageMagick-6/policy.xml || echo "policy.xml not found or cannot be read"

# Set the working directory
WORKDIR /app

# Create a non-root user and group
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy only the necessary files first to leverage Docker cache
COPY requirements.txt .
COPY application.py .
COPY process_video.py .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy remaining application code
COPY templates/ templates/
COPY static/ static/

# Ensure FFmpeg has execute permissions
RUN chmod +x /bin/ffmpeg

# Change ownership of the app directory
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Create necessary directories
RUN mkdir -p uploads static/translated_videos

# Set environment variables for Flask
ENV FLASK_APP=application.py
ENV FLASK_RUN_HOST=0.0.0.0

# Command to run on container start
CMD ["gunicorn", "application:app", "--bind", "0.0.0.0:$PORT"]
