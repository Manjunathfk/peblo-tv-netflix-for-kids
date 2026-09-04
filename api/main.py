from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://peblo:peblo123@db:5432/peblo")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

app = FastAPI(title="Peblo TV Mini")

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/health")
def health():
    return {"status": "ok", "storage": "local"}

@app.get("/")
def root():
    return {"msg": "Peblo TV Mini API running"}