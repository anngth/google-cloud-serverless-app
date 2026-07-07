# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.11-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Set working directory
ENV APP_HOME /app
WORKDIR $APP_HOME

# Install dependencies first (to leverage Docker build cache)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY src/ ./src/

# Run the web service on container startup. Here we use the gunicorn
# webserver, targeting the Flask app 'app' inside the package 'src.app'.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 src.app:app
