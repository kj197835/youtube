import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

# Database Configuration
DB_NAME = "youtube_data.db"
Base = declarative_base()

class Channel(Base):
    __tablename__ = 'channels'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    profile_image = Column(String)
    last_updated = Column(DateTime, default=datetime.utcnow)

    # Relationships
    daily_stats = relationship("DailyStat", back_populates="channel", cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="channel", cascade="all, delete-orphan")

class DailyStat(Base):
    __tablename__ = 'daily_stats'

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(String, ForeignKey('channels.id'), nullable=False)
    date = Column(Date, nullable=False)
    
    # Metrics
    views = Column(Integer, default=0)
    subscribers = Column(Integer, default=0)
    video_count = Column(Integer, default=0)
    revenue = Column(Float, default=0.0)
    watch_time_hours = Column(Float, default=0.0)
    avg_engagement_rate = Column(Float, nullable=True)

    channel = relationship("Channel", back_populates="daily_stats")

class Video(Base):
    __tablename__ = 'videos'

    id = Column(String, primary_key=True) # Video ID from YouTube
    channel_id = Column(String, ForeignKey('channels.id'), nullable=False)
    title = Column(String)
    thumbnail_url = Column(String)
    published_at = Column(DateTime)
    
    channel = relationship("Channel", back_populates="videos")
    stats = relationship("VideoStat", back_populates="video", cascade="all, delete-orphan")

class VideoStat(Base):
    __tablename__ = 'video_stats'

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, ForeignKey('videos.id'), nullable=False)
    date = Column(Date, default=datetime.utcnow().date)
    
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    revenue = Column(Float, default=0.0)

    video = relationship("Video", back_populates="stats")

# Database Setup
engine = create_engine(f'sqlite:///{DB_NAME}', echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """Initialize the database and create tables."""
    print(f"Initializing database: {DB_NAME}")
    Base.metadata.create_all(engine)

def get_session():
    """Return a new database session."""
    return SessionLocal()
