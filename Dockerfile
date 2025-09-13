FROM python:3.12-slim

WORKDIR /app

# Install and use uv in single command
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    ~/.cargo/bin/uv pip install --system -e /app/mpcs/adan

# Copy all files after dependencies are installed
COPY . /app

EXPOSE 8000
CMD ["python", "/app/mpcs/adan/main.py"]