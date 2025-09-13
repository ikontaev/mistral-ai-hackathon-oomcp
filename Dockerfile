FROM python:3.13-slim

# Install required dependencies
RUN apt-get update && \
    apt-get install -y curl git && \
    rm -rf /var/lib/apt/lists/*

# Install uv using pip
RUN pip install uv

WORKDIR /app

# Copy only the requirements files first for better layer caching
COPY mpcs/adan/pyproject.toml mpcs/adan/
COPY mpcs/adan/uv.lock mpcs/adan/

# Install dependencies
RUN uv pip install --system -e /app/mpcs/adan

# Copy the rest of the application (including stdlib)
COPY mpcs/adan/ /app/mpcs/adan/

# Copy other root files if needed (Dockerfile, docker-compose.yml, etc.)
COPY . /app/

EXPOSE 8000
CMD ["uv", "run", "/app/mpcs/adan/main.py"]