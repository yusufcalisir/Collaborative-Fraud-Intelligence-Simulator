FROM python:3.12-slim

# Install system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend requirements and install dependencies globally as root
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Create non-root user for Hugging Face Spaces compliance
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8

# Copy backend application source files with owner permissions
COPY --chown=user backend/app ./app
COPY --chown=user backend/alembic ./alembic
COPY --chown=user backend/alembic.ini .

# Expose the default Hugging Face Spaces port
EXPOSE 7860

# Start backend application via python module to ensure clean module path loading
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
