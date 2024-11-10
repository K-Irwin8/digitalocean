FROM python:3.12-slim-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV XDG_CACHE_HOME=/app/.cache  
ENV FFMPEG_BINARY=/usr/bin/ffmpeg
ENV PATH="/usr/bin:${PATH}"

# Install necessary system packages and dependencies for ImageMagick
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    libpulse0 \
    build-essential \
    libmagick++-dev \
    fonts-liberation \
    sox \
    bc \
    gsfonts \
    && rm -rf /var/lib/apt/lists/*

# Install ImageMagick from source for better compatibility
RUN mkdir -p /tmp/distr && \
    cd /tmp/distr && \
    wget https://download.imagemagick.org/ImageMagick/download/releases/ImageMagick-7.0.11-2.tar.xz && \
    tar xvf ImageMagick-7.0.11-2.tar.xz && \
    cd ImageMagick-7.0.11-2 && \
    ./configure --enable-shared=yes --disable-static --without-perl && \
    make && \
    make install && \
    ldconfig /usr/local/lib && \
    cd /tmp && \
    rm -rf distr

# Modify ImageMagick's policy.xml to allow @ paths
RUN sed -i 's/<policy domain="path" rights="none" pattern="@\*"\/>/<\!-- & -->/' /etc/ImageMagick-6/policy.xml

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
