FROM python:3.13.13

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY migrations/ ./migrations/
COPY tests/ ./tests/
COPY alembic.ini ./

RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8000

CMD ["fastapi", "run", "src/main.py", "--port", "8000", "--workers", "4"]
