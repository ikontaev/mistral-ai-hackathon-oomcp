FROM python:3.12-slim

WORKDIR /app

# Install uv using the official install script
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy requirements first for better layer caching
COPY mpcs/adan/pyproject.toml mpcs/adan/
COPY mpcs/adan/uv.lock mpcs/adan/

# Install dependencies using uv
RUN ~/.cargo/bin/uv pip install --system -e /app/mpcs/adan

# Copy the rest of the application
COPY . /app

EXPOSE 8000
CMD ["python", "/app/mpcs/adan/main.py"]