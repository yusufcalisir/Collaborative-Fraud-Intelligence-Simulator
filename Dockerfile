FROM python:3.12-slim

# Install system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create non-root user for Hugging Face Spaces compliance
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# Copy backend requirements and install dependencies
COPY --chown=user backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy backend application source files
COPY --chown=user backend/app ./app
COPY --chown=user backend/alembic ./alembic
COPY --chown=user backend/alembic.ini .

# Expose the default Hugging Face Spaces port
EXPOSE 7860

# Start backend application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
