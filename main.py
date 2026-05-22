from fastapi import FastAPI
from src.routers import router

app = FastAPI()
app.include_router(router)

