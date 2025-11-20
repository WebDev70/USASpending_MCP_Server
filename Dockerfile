# Multi-stage build for smaller final image
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 appuser

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY src/ /app/src/
COPY docs/ /app/docs/
COPY pyproject.toml .
COPY docker-entrypoint.sh /app/

# Set environment variables
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install the package
RUN pip install --user --no-cache-dir -e .

# Change ownership to appuser
RUN chown -R appuser:appuser /app && chmod +x /app/docker-entrypoint.sh

# Switch to non-root user
USER appuser

# Expose the port
EXPOSE 3002

# Health check - test if the server is responding on port 3002
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3002/ || exit 1

# Run the server using the entrypoint script which binds to 0.0.0.0
ENTRYPOINT ["/app/docker-entrypoint.sh"]
