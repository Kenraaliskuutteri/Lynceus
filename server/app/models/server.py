from sqlalchemy import Column, String, DateTime

from app.core.database import Base


class Server(Base):
    __tablename__ = "servers"

    id = Column(String, primary_key=True)
    hostname = Column(String, nullable=False)
    ip_address = Column(String, nullable=False, default="unknown")
    last_seen = Column(DateTime, nullable=True)