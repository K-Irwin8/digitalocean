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
    && rm -rf /var/lib/apt/lists/*

# Verify ImageMagick installation and locate policy.xml
RUN imagemagick --version && find /etc -name "policy.xml"

# Modify ImageMagick's policy.xml to allow @ paths
RUN sed -i '/<policy domain="path" rights="none" pattern="@*"/>/ s/^#*/#/' /etc/ImageMagick-6/policy.xml

# Verify the modification
RUN grep '<policy domain="path" rights="none" pattern="@*"/>' /etc/ImageMagick-6/policy.xml && echo "ImageMagick policy modified successfully."

# Set the working directory in the container
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

# Copy fonts if using custom fonts
COPY fonts/ fonts/

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
