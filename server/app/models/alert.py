from sqlalchemy import Column, Integer, String, Float, DateTime

from app.core.database import Base


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    server_id = Column(String, index=True, nullable=False)
    metric = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="triggered")
    triggered_at = Column(DateTime, nullable=False)
    resolved_at = Column(DateTime, nullable=True)