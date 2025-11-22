# Use a slim Python base image
FROM python:3.11-slim

# Set environment variables for non-interactive commands
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copy the .env file (for project settings) and the code
COPY rag_agent/.env /app/rag_agent/.env
COPY . /app

# Set the working directory
WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port used by the service (typically 8080 for Cloud Run)
ENV PORT 8080
EXPOSE 8080

# The startup command for the container
CMD ["uvicorn", "rag_agent.main:app", "--host", "0.0.0.0", "--port", "8080"]
