from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Show(Base):
    __tablename__ = "shows"
    id = Column(String, primary_key=True)
    title = Column(String)
    section = Column(String)
    category = Column(String)
    synopsis = Column(String)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Season(Base):
    __tablename__ = "seasons"
    id = Column(String, primary_key=True)
    show_id = Column(String, ForeignKey("shows.id"))
    title = Column(String)
    season_number = Column(Integer)

class Episode(Base):
    __tablename__ = "episodes"
    id = Column(String, primary_key=True)
    show_id = Column(String, ForeignKey("shows.id"))
    season_id = Column(String, ForeignKey("seasons.id"))
    title = Column(String)
    episode_number = Column(Integer)
    video_url = Column(String)
    duration = Column(Integer)
    synopsis = Column(String)