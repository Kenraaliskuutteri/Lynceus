from sqlalchemy import Column, Integer, String, Float, DateTime

from app.core.database import Base


class MetricLog(Base):
    __tablename__ = "metric_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    server_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    cpu_usage = Column(Float, nullable=False)
    ram_usage = Column(Float, nullable=False)
    disk_usage = Column(Float, nullable=False)
    network_rx_kb = Column(Float, nullable=False)
    network_tx_kb = Column(Float, nullable=False)