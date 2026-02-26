FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=6969

WORKDIR /app

COPY pyproject.toml README.md server.py connector.py ./

RUN pip install --no-cache-dir .

EXPOSE 6969

CMD ["trapdoor", "--host", "0.0.0.0", "--port", "6969", "--no-interactive"]
