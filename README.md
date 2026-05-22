# Test Task

A FastAPI application for managing a department/employee hierarchy, backed by PostgreSQL.

## Requirements

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)


## Getting started

```bash
git clone https://github.com/Vitalii-Kh95/department_test_task.git
cd department_test_task
```


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

## Notes

Написал тесты чтобы было понятно какие баги и условия пытался учесть.

В ТЗ было написано: "Частые ошибки: ...  смешивание бизнес-логики и работы с БД." Но ради простоты я отчасти так и сделал. И модели pydantic и модели бд в одном файле - `models.py`; Бизнес логика  смешана с обработкой http запросов и находится в одном файле - `routers.py`. В остальном старался следовать ТЗ и замечаниям в нём.