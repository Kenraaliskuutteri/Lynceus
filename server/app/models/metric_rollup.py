from sqlalchemy import Column, DateTime, Float, Integer, String, UniqueConstraint

from app.core.database import Base


class MetricRollup(Base):
    __tablename__ = "metric_rollups"
    __table_args__ = (UniqueConstraint("server_id", "bucket_start", name="uq_rollup_server_bucket"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    server_id = Column(String, index=True, nullable=False)
    bucket_start = Column(DateTime, index=True, nullable=False)
    samples = Column(Integer, nullable=False)
    cpu_avg = Column(Float, nullable=False)
    cpu_max = Column(Float, nullable=False)
    ram_avg = Column(Float, nullable=False)
    ram_max = Column(Float, nullable=False)
    disk_avg = Column(Float, nullable=False)
    disk_max = Column(Float, nullable=False)
    rx_avg = Column(Float, nullable=False)
    rx_max = Column(Float, nullable=False)
    tx_avg = Column(Float, nullable=False)
    tx_max = Column(Float, nullable=False)