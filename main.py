from fastapi import FastAPI
from db import models
from db.database import engine
from api import routes

models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="Vaayu - The GenAI Guardian Angel")
app.include_router(routes.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Vaayu - The GenAI Guardian Angel"}