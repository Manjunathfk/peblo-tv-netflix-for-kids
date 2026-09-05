import os, json, uuid
from datetime import datetime
from typing import Optional, Dict
from fastapi import FastAPI, HTTPException, UploadFile, File, Depends, Query, Header
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from PIL import Image
import io

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://peblo:peblo@db:5432/peblotv")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Show(Base):
    __tablename__ = "shows"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    section = Column(String, nullable=True)
    status = Column(String, default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)

class Season(Base):
    __tablename__ = "seasons"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    show_id = Column(String, ForeignKey("shows.id"))
    season_number = Column(Integer, nullable=False)
    title = Column(String)

class Episode(Base):
    __tablename__ = "episodes"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    show_id = Column(String, ForeignKey("shows.id"))
    season_id = Column(String, ForeignKey("seasons.id"))
    title = Column(String, nullable=False)
    content_group = Column(String, nullable=False)
    language = Column(String, nullable=False)
    duration_sec = Column(Integer, nullable=True)
    status = Column(String, default="draft")
    __table_args__ = (UniqueConstraint('content_group', 'language', name='uq_cg_lang'),)

class Artwork(Base):
    __tablename__ = "artworks"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    show_id = Column(String, ForeignKey("shows.id"), nullable=True)
    episode_id = Column(String, ForeignKey("episodes.id"), nullable=True)
    type = Column(String)
    path = Column(String)
    width = Column(Integer)
    height = Column(Integer)
    size_kb = Column(Integer)

class PublishRun(Base):
    __tablename__ = "publish_runs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    when = Column(DateTime, default=datetime.utcnow)
    who = Column(String)
    shows_count = Column(Integer)
    episodes_count = Column(Integer)
    outcome = Column(String)

def init_db():
    Base.metadata.create_all(bind=engine)

app = FastAPI(title="Peblo TV Mini API", version="v1")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_role(x_role: Optional[str] = Header(None)):
    return x_role or "editor"

def require_admin(role: str = Depends(get_role)):
    if role!= "admin":
        raise HTTPException(403, "Admin only - send header X-Role: admin")
    return role

class ShowCreate(BaseModel):
    title: str
    section: Optional[str] = None
class SeasonCreate(BaseModel):
    show_id: str
    season_number: int
    title: Optional[str] = None
class EpisodeCreate(BaseModel):
    show_id: str
    season_id: str
    title: str
    content_group: str
    language: str
    duration_sec: Optional[int] = None

STORAGE_DIR = "/data"
CATALOGUE_PATH = os.path.join(STORAGE_DIR, "catalogue.json")

@app.get("/health")
def health():
    return {"status": "ok", "catalogue_version": "v1"}

@app.post("/shows")
def create_show(payload: ShowCreate, db: Session = Depends(get_db)):
    s = Show(title=payload.title, section=payload.section)
    db.add(s); db.commit(); db.refresh(s)
    return {"id": s.id, "title": s.title, "section": s.section, "created_at": s.created_at}

@app.get("/shows")
def list_shows(db: Session = Depends(get_db)):
    shows = db.query(Show).all()
    return [{"id": sh.id, "title": sh.title, "section": sh.section, "status": sh.status, "created_at": sh.created_at} for sh in shows]

@app.post("/seasons")
def create_season(payload: SeasonCreate, db: Session = Depends(get_db)):
    season = Season(show_id=payload.show_id, season_number=payload.season_number, title=payload.title)
    db.add(season); db.commit(); db.refresh(season)
    return season

@app.get("/seasons")
def list_seasons(show_id: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Season)
    if show_id: q = q.filter(Season.show_id == show_id)
    return q.all()

@app.post("/episodes")
def create_episode(payload: EpisodeCreate, db: Session = Depends(get_db)):
    ep = Episode(**payload.dict())
    db.add(ep)
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, f"content_group+language must be unique: {e}")
    db.refresh(ep)
    return ep

@app.get("/episodes")
def list_episodes(show_id: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Episode)
    if show_id: q = q.filter(Episode.show_id == show_id)
    return q.all()

@app.post("/artwork/upload")
def upload_artwork(show_id: Optional[str] = None, episode_id: Optional[str] = None, type: str = Query(..., description="poster/banner/thumbnail"), file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = file.file.read()
    size_kb = len(content) / 1024
    if size_kb > 200:
        raise HTTPException(400, f"File too large {size_kb:.1f}KB > 200KB")
    try:
        img = Image.open(io.BytesIO(content))
        w,h = img.size
    except:
        raise HTTPException(400, "Invalid image")
    if type == "poster" and not (abs(w/h - 2/3) < 0.2):
        raise HTTPException(400, f"Poster must be 2:3 approx 600x900, got {w}x{h}")
    if type in ["banner","thumbnail"] and not (abs(w/h - 16/9) < 0.3):
        raise HTTPException(400, f"{type} must be 16:9 approx, got {w}x{h}")
    os.makedirs(STORAGE_DIR, exist_ok=True)
    fname = f"{uuid.uuid4()}_{file.filename}"
    fpath = os.path.join(STORAGE_DIR, fname)
    with open(fpath, "wb") as f:
        f.write(content)
    art = Artwork(show_id=show_id, episode_id=episode_id, type=type, path=fpath, width=w, height=h, size_kb=int(size_kb))
    db.add(art); db.commit(); db.refresh(art)
    return art

@app.post("/admin/catalog/publish")
def publish_catalog(role: str = Depends(require_admin), db: Session = Depends(get_db)):
    shows = db.query(Show).filter(Show.status=="published").all()
    episodes = db.query(Episode).filter(Episode.status=="published").all()
    valid_eps = []
    for ep in episodes:
        has_art = db.query(Artwork).filter(Artwork.episode_id==ep.id).first()
        if not has_art or not ep.duration_sec:
            continue
        valid_eps.append(ep)
    grouped: Dict[str, dict] = {}
    for ep in valid_eps:
        cg = ep.content_group
        if cg not in grouped:
            grouped[cg] = {"content_group": cg, "title": ep.title, "show_id": ep.show_id, "languages": [], "episodes": []}
        if ep.language not in grouped[cg]["languages"]:
            grouped[cg]["languages"].append(ep.language)
        grouped[cg]["episodes"].append({"id": ep.id, "language": ep.language, "duration_sec": ep.duration_sec})
    catalogue = {"sections": {}, "generated_at": datetime.utcnow().isoformat(), "version": "v1"}
    for sh in shows:
        sec = sh.section or "uncategorized"
        if sec not in catalogue["sections"]:
            catalogue["sections"][sec] = []
        show_collapsed = [v for v in grouped.values() if v["show_id"]==sh.id]
        show_collapsed.sort(key=lambda x: x["title"])
        catalogue["sections"][sec].append({"show_id": sh.id, "title": sh.title, "episodes": show_collapsed})
    os.makedirs(STORAGE_DIR, exist_ok=True)
    tmp_path = CATALOGUE_PATH + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(catalogue, f, indent=2)
    os.rename(tmp_path, CATALOGUE_PATH)
    run = PublishRun(who=role, shows_count=len(shows), episodes_count=len(valid_eps), outcome="success")
    db.add(run); db.commit()
    return {"status": "published", "path": CATALOGUE_PATH, "shows": len(shows), "episodes": len(valid_eps), "run_id": run.id}

@app.get("/catalog")
def get_catalog():
    if not os.path.exists(CATALOGUE_PATH):
        raise HTTPException(404, "Not published yet, POST /admin/catalog/publish as admin")
    with open(CATALOGUE_PATH) as f:
        return json.load(f)

@app.get("/catalog/search")
def search_catalog(q: str = Query(""), language: Optional[str] = None, section: Optional[str] = None):
    if not os.path.exists(CATALOGUE_PATH):
        raise HTTPException(404, "Not published")
    with open(CATALOGUE_PATH) as f:
        cat = json.load(f)
    results = []
    q_lower = q.lower()
    for sec, shows in cat.get("sections", {}).items():
        if section and sec!= section: continue
        for sh in shows:
            if q_lower and q_lower not in sh["title"].lower():
                if not any(q_lower in ep["title"].lower() for ep in sh.get("episodes", [])):
                    continue
            filtered_eps = sh.get("episodes", [])
            if language:
                filtered_eps = [ep for ep in filtered_eps if language in ep.get("languages", [])]
            results.append({"section": sec, "show": sh["title"], "episodes": filtered_eps})
    return {"query": q, "results": results}

@app.get("/admin/validation-report")
def validation_report(db: Session = Depends(get_db)):
    issues = []
    eps = db.query(Episode).all()
    for ep in eps:
        has_art = db.query(Artwork).filter(Artwork.episode_id==ep.id).first()
        if not has_art:
            issues.append({"type": "missing_artwork", "episode_id": ep.id, "title": ep.title})
        if not ep.duration_sec:
            issues.append({"type": "missing_duration", "episode_id": ep.id, "title": ep.title})
    shows = db.query(Show).filter(Show.status=="published").all()
    for sh in shows:
        if not sh.section:
            issues.append({"type": "missing_section", "show_id": sh.id, "title": sh.title})
    grouped = {}
    for iss in issues:
        grouped.setdefault(iss["type"], []).append(iss)
    return {"total_issues": len(issues), "grouped": grouped, "details": issues}

@app.put("/shows/{show_id}/publish")
def publish_show(show_id: str, db: Session = Depends(get_db)):
    sh = db.query(Show).filter(Show.id==show_id).first()
    if not sh: raise HTTPException(404, "Not found")
    if not sh.section: raise HTTPException(400, "Published show must have section")
    has_art = db.query(Artwork).filter(Artwork.show_id==show_id).first()
    if not has_art: raise HTTPException(400, "Need artwork")
    sh.status = "published"; db.commit()
    return {"status": "published"}

@app.put("/episodes/{ep_id}/publish")
def publish_episode(ep_id: str, db: Session = Depends(get_db)):
    ep = db.query(Episode).filter(Episode.id==ep_id).first()
    if not ep: raise HTTPException(404, "Not found")
    has_art = db.query(Artwork).filter(Artwork.episode_id==ep_id).first()
    if not has_art or not ep.duration_sec: raise HTTPException(400, "Need artwork+duration")
    ep.status = "published"; db.commit()
    return {"status": "published"}

@app.on_event("startup")
def startup():
    init_db()