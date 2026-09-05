from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import os
import uuid
from datetime import datetime
import time
from models import Base   # <-- ADD THIS

app = FastAPI()   # <-- ADD THIS

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://peblo:peblo123@db:5432/peblo") # <-- ADD THIS
engine = create_engine(DATABASE_URL) # <-- ADD THIS

@app.on_event("startup")
def startup():
    for i in range(10):
        try:
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
            print("DB Connected!")
            break
        except Exception as e:
            print(f"Waiting for DB... {i}")
            time.sleep(2)

from models import Base, Show, Season, Episode

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://peblo:peblo123@db:5432/peblo")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI(title="Peblo TV - Netflix for Kids")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
@app.get("/health")
def health():
    return {"status": "ok", "catalogue_version": "v1"}
@app.on_event("startup")
def startup():
    # This fixes your 500 error - deletes old table
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

# ========== SHOWS ==========
@app.post("/shows")
def create_show(data: dict, db: Session = Depends(get_db)):
    show_id = uuid.uuid4().hex[:8]
    new_show = Show(
        id=show_id,
        title=data.get("title"),
        section=data.get("section"),
        category=data.get("category"),
        synopsis=data.get("synopsis"),
        status=data.get("status"),
        created_at=datetime.utcnow()
    )
    db.add(new_show)
    db.commit()
    db.refresh(new_show)
    return new_show

@app.get("/shows")
def get_shows(db: Session = Depends(get_db)):
    return db.query(Show).all()

@app.get("/shows/{show_id}")
def get_show(show_id: str, db: Session = Depends(get_db)):
    show = db.query(Show).filter(Show.id == show_id).first()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    
    seasons = db.query(Season).filter(Season.show_id == show_id).all()
    result_seasons = []
    for s in seasons:
        episodes = db.query(Episode).filter(Episode.season_id == s.id).all()
        result_seasons.append({
            "id": s.id,
            "title": s.title,
            "season_number": s.season_number,
            "episodes": episodes
        })
    
    return {
        "id": show.id,
        "title": show.title,
        "section": show.section,
        "category": show.category,
        "synopsis": show.synopsis,
        "status": show.status,
        "seasons": result_seasons
    }

# ========== SEASONS ==========
@app.post("/shows/{show_id}/seasons")
def create_season(show_id: str, data: dict, db: Session = Depends(get_db)):
    show = db.query(Show).filter(Show.id == show_id).first()
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    
    season_id = uuid.uuid4().hex[:8]
    new_season = Season(
        id=season_id,
        show_id=show_id,
        title=data.get("title"),
        season_number=data.get("season_number")
    )
    db.add(new_season)
    db.commit()
    db.refresh(new_season)
    return new_season

@app.get("/shows/{show_id}/seasons")
def get_seasons(show_id: str, db: Session = Depends(get_db)):
    return db.query(Season).filter(Season.show_id == show_id).all()

# ========== EPISODES ==========
@app.post("/seasons/{season_id}/episodes")
def create_episode(season_id: str, data: dict, db: Session = Depends(get_db)):
    season = db.query(Season).filter(Season.id == season_id).first()
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")
    
    episode_id = uuid.uuid4().hex[:8]
    new_ep = Episode(
        id=episode_id,
        show_id=season.show_id,
        season_id=season_id,
        title=data.get("title"),
        episode_number=data.get("episode_number"),
        video_url=data.get("video_url"),
        duration=data.get("duration"),
        synopsis=data.get("synopsis")
    )
    db.add(new_ep)
    db.commit()
    db.refresh(new_ep)
    return new_ep

@app.get("/seasons/{season_id}/episodes")
def get_episodes(season_id: str, db: Session = Depends(get_db)):
    return db.query(Episode).filter(Episode.season_id == season_id).all()