from sqlalchemy import Column, String, DateTime, Float, Integer

from app.core.database import Base


class Server(Base):
    __tablename__ = "servers"

    id = Column(String, primary_key=True)
    hostname = Column(String, nullable=False)
    ip_address = Column(String, nullable=False, default="unknown")
    last_seen = Column(DateTime, nullable=True)
    cpu_threshold = Column(Float, nullable=True)
    ram_threshold = Column(Float, nullable=True)
    disk_threshold = Column(Float, nullable=True)
    offline_threshold_seconds = Column(Integer, nullable=True)