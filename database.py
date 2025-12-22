import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean, UniqueConstraint
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
    daily_stats = relationship("ChannelDaily", back_populates="channel", cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="channel", cascade="all, delete-orphan")

class ChannelDaily(Base):
    """Daily channel-wide statistics"""
    __tablename__ = 'channel_daily_stats'

    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(String, ForeignKey('channels.id'), nullable=False)
    date = Column(Date, nullable=False)
    
    views = Column(Integer, default=0)
    estimated_revenue = Column(Float, default=0.0)
    watch_time_minutes = Column(Float, default=0.0)
    subscribers_gained = Column(Integer, default=0)
    
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    avg_view_duration_seconds = Column(Float, default=0.0)
    
    # Ensure unique record per day per channel
    __table_args__ = (UniqueConstraint('channel_id', 'date', name='uix_channel_date'),)

    channel = relationship("Channel", back_populates="daily_stats")

class Video(Base):
    """Static or slowly changing video metadata"""
    __tablename__ = 'videos'

    id = Column(String, primary_key=True) # Video ID
    channel_id = Column(String, ForeignKey('channels.id'), nullable=False)
    
    title = Column(String)
    thumbnail_url = Column(String)
    published_at = Column(DateTime)
    
    # New Fields
    is_shorts = Column(Boolean, default=False)
    video_length = Column(String) # e.g. "PT5M30S" or Seconds as Integer? Keeping String as usually returned by API duration
    
    channel = relationship("Channel", back_populates="videos")
    daily_stats = relationship("VideoDaily", back_populates="video", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="video", cascade="all, delete-orphan")

class VideoDaily(Base):
    """Daily statistics per video"""
    __tablename__ = 'video_daily_stats'

    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(String, ForeignKey('videos.id'), nullable=False)
    date = Column(Date, nullable=False)
    
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    
    estimated_revenue = Column(Float, default=0.0)
    watch_time_minutes = Column(Float, default=0.0)
    subscribers_gained = Column(Integer, default=0)

    # Unique constraint to prevent duplicate day entries for a video
    __table_args__ = (UniqueConstraint('video_id', 'date', name='uix_video_date'),)

    video = relationship("Video", back_populates="daily_stats")

class Comment(Base):
    """Video Comments"""
    __tablename__ = 'video_comments'
    
    id = Column(String, primary_key=True) # Comment ID
    video_id = Column(String, ForeignKey('videos.id'), nullable=False)
    
    author_name = Column(String)
    text = Column(Text)
    published_at = Column(DateTime)
    like_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)
    
    # Store the fetch date if we want to track when we saw it? 
    # Usually comments are static unless edited, but for analytics 'comment_day' usually refers to published_at
    
    video = relationship("Video", back_populates="comments")

# --- Detailed Analytics Tables ---

class DemographicsAge(Base):
    __tablename__ = 'daily_demographics_age'
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    
    age_group = Column(String, nullable=False) # e.g. "age25-34"
    viewer_percentage = Column(Float, default=0.0) # Often API gives %
    
    # Can we store absolute numbers? API usually gives % for channel, or views for dimensions.
    # Assuming we fetch "views" broken down by age
    views = Column(Integer, default=0)
    watch_time_minutes = Column(Float, default=0.0)
    
    __table_args__ = (UniqueConstraint('date', 'age_group', name='uix_date_age'),)

class DemographicsGender(Base):
    __tablename__ = 'daily_demographics_gender'
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    
    gender = Column(String, nullable=False) # "male", "female", "user_specified"
    views = Column(Integer, default=0)
    watch_time_minutes = Column(Float, default=0.0)
    
    __table_args__ = (UniqueConstraint('date', 'gender', name='uix_date_gender'),)

class Geography(Base):
    __tablename__ = 'daily_geography'
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    
    country_code = Column(String, nullable=False) # "KR", "US"
    views = Column(Integer, default=0)
    watch_time_minutes = Column(Float, default=0.0)
    
    __table_args__ = (UniqueConstraint('date', 'country_code', name='uix_date_geo'),)

class TrafficSource(Base):
    __tablename__ = 'daily_traffic_sources'
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    
    source_type = Column(String, nullable=False) # "YT_SEARCH", "RELATED_VIDEO"
    views = Column(Integer, default=0)
    watch_time_minutes = Column(Float, default=0.0)
    
    __table_args__ = (UniqueConstraint('date', 'source_type', name='uix_date_traffic'),)


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
