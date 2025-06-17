FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Set default API keys to empty values (will be overridden by docker-compose or .env)
ENV OPENAI_API_KEY=""
ENV GROK_API_KEY=""
ENV GROK_API_URL="https://api.x.ai/v1/chat/completions"
ENV DJANGO_SETTINGS_MODULE="formsiq_project.settings"

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy project
COPY . .

# Create staticfiles directory
RUN mkdir -p /app/staticfiles

# Collect static files (minimal static files for Django admin only)
RUN python manage.py collectstatic --noinput || echo "Static files collection skipped."

# Create media directory
RUN mkdir -p /app/media/pdf/output
RUN chmod -R 755 /app/media

# Create a health check script
RUN echo '#!/bin/bash\nset -e\npython -c "from openai import OpenAI; print(\"OpenAI client loaded successfully\")"' > /app/healthcheck.sh
RUN chmod +x /app/healthcheck.sh

# Expose port
EXPOSE 8000

# Start gunicorn with increased timeout
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "120", "formsiq_project.wsgi:application"] 