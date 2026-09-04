from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
import datetime
Base = declarative_base()

class Show(Base):
    __tablename__ = "shows"
    id = Column(String, primary_key=True)
    title = Column(String)
    section = Column(String)
    category = Column(String)
    status = Column(String, default="draft")
    synopsis = Column(String)

class Season(Base):
    __tablename__ = "seasons"
    id = Column(String, primary_key=True)
    show_id = Column(String, ForeignKey("shows.id"))
    number = Column(Integer)
    title = Column(String)

class Episode(Base):
    __tablename__ = "episodes"
    id = Column(String, primary_key=True)
    season_id = Column(String, ForeignKey("seasons.id"))
    title = Column(String)
    duration = Column(Integer)
    content_group = Column(String)
    language = Column(String)
    status = Column(String, default="draft")
    __table_args__ = (UniqueConstraint('content_group', 'language', name='uq_group_lang'),)

class Artwork(Base):
    __tablename__ = "artworks"
    id = Column(String, primary_key=True)
    episode_id = Column(String, ForeignKey("episodes.id"))
    type = Column(String)
    path = Column(String)
    width = Column(Integer)
    height = Column(Integer)
    size_kb = Column(Integer)

class PublishRun(Base):
    __tablename__ = "publish_runs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    who = Column(String)
    when = Column(DateTime, default=datetime.datetime.utcnow)
    counts = Column(String)
    outcome = Column(String)