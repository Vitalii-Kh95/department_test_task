# Test Task

A FastAPI application for managing a department/employee hierarchy, backed by PostgreSQL.

## Requirements

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)


## Getting started

```bash
git clone <repository-url>
cd test_task
```


## Configuration

При необходимости отредактировать переменные окружения в файле: `.env`:


## Running the application

```bash
docker compose up --build -d
```

API: **http://localhost:8000**.  
Interactive docs: **http://localhost:8000/docs**


## Running tests

```bash
docker compose run --rm test
```