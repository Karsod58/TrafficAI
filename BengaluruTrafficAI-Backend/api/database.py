"""
BengaluruTrafficAI — Database Models
Component 4a: SQLAlchemy models for violations, cameras, and analytics.
Uses SQLite for development (zero setup). Swap DATABASE_URL for PostgreSQL in production.
"""

from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, Float, Integer,
    Boolean, DateTime, Index
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bengaluru_traffic.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    poolclass=StaticPool if DATABASE_URL.startswith("sqlite") else None,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class ViolationRecord(Base):
    __tablename__ = "violations"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    event_id       = Column(String(16), unique=True, index=True)
    violation_type = Column(String(40), index=True)
    camera_id      = Column(String(20), index=True)
    track_id       = Column(Integer, nullable=True)
    plate_number   = Column(String(20), nullable=True, index=True)
    confidence     = Column(Float)
    severity       = Column(Integer)
    fine_inr       = Column(Integer)
    auto_approve   = Column(Boolean, default=False)
    reviewed       = Column(Boolean, default=False)
    approved       = Column(Boolean, nullable=True)
    frame_idx      = Column(Integer)
    bbox_x1        = Column(Integer, nullable=True)
    bbox_y1        = Column(Integer, nullable=True)
    bbox_x2        = Column(Integer, nullable=True)
    bbox_y2        = Column(Integer, nullable=True)
    image_path     = Column(String(256), nullable=True)
    image_hash     = Column(String(64), nullable=True)
    timestamp      = Column(Float, index=True)
    created_at     = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_viol_type_time", "violation_type", "timestamp"),
        Index("ix_cam_time",       "camera_id",      "timestamp"),
    )

    def to_dict(self) -> dict:
        return {
            "id":             self.id,
            "event_id":       self.event_id,
            "violation_type": self.violation_type,
            "camera_id":      self.camera_id,
            "track_id":       self.track_id,
            "plate_number":   self.plate_number,
            "confidence":     round(self.confidence, 3),
            "severity":       self.severity,
            "fine_inr":       self.fine_inr,
            "auto_approve":   self.auto_approve,
            "reviewed":       self.reviewed,
            "approved":       self.approved,
            "image_path":     self.image_path,
            "timestamp":      self.timestamp,
            "created_at":     self.created_at.isoformat() if self.created_at else None,
        }


class CameraRecord(Base):
    __tablename__ = "cameras"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    camera_id   = Column(String(20), unique=True, index=True)
    name        = Column(String(100))
    location    = Column(String(200))
    lat         = Column(Float, nullable=True)
    lon         = Column(Float, nullable=True)
    stream_url  = Column(String(300), nullable=True)
    roi_path    = Column(String(256), nullable=True)
    active      = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "camera_id":  self.camera_id,
            "name":       self.name,
            "location":   self.location,
            "lat":        self.lat,
            "lon":        self.lon,
            "active":     self.active,
        }


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    hour_bucket    = Column(String(20), index=True)
    camera_id      = Column(String(20))
    violation_type = Column(String(40))
    count          = Column(Integer, default=0)
    avg_confidence = Column(Float, default=0.0)
    created_at     = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


def seed_demo_cameras():
    with get_db() as db:
        if db.query(CameraRecord).count() > 0:
            return
        cameras = [
            CameraRecord(camera_id="cam_01", name="Silk Board Junction",     location="Silk Board, Bengaluru",      lat=12.9178, lon=77.6227),
            CameraRecord(camera_id="cam_02", name="Marathahalli Bridge",      location="Marathahalli, Bengaluru",    lat=12.9560, lon=77.7012),
            CameraRecord(camera_id="cam_03", name="Hebbal Flyover",           location="Hebbal, Bengaluru",          lat=13.0358, lon=77.5970),
            CameraRecord(camera_id="cam_04", name="MG Road Junction",         location="MG Road, Bengaluru",         lat=12.9753, lon=77.6066),
            CameraRecord(camera_id="cam_05", name="Electronic City Toll",     location="Electronic City, Bengaluru", lat=12.8399, lon=77.6770),
            CameraRecord(camera_id="cam_06", name="Koramangala 80ft Road",    location="Koramangala, Bengaluru",     lat=12.9340, lon=77.6270),
            CameraRecord(camera_id="cam_07", name="Whitefield ORR Junction",  location="Whitefield, Bengaluru",      lat=12.9698, lon=77.7499),
            CameraRecord(camera_id="cam_08", name="Indiranagar 100ft Road",   location="Indiranagar, Bengaluru",     lat=12.9784, lon=77.6408),
            CameraRecord(camera_id="cam_09", name="Yeshwanthpur Circle",      location="Yeshwanthpur, Bengaluru",    lat=13.0213, lon=77.5530),
            CameraRecord(camera_id="cam_10", name="Bannerghatta Road Signal", location="Bannerghatta, Bengaluru",    lat=12.8955, lon=77.5975),
            CameraRecord(camera_id="cam_11", name="Rajajinagar Circle",       location="Rajajinagar, Bengaluru",     lat=12.9920, lon=77.5520),
            CameraRecord(camera_id="cam_12", name="KR Puram Bridge",          location="KR Puram, Bengaluru",        lat=13.0074, lon=77.6963),
        ]
        db.add_all(cameras)
        db.commit()


@contextmanager
def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
