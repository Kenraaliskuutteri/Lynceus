from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SystemMetrics(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    timestamp: int
    cpu_usage: float = Field(alias="cpuUsage")
    ram_usage: float = Field(alias="ramUsage")
    disk_usage: float = Field(alias="diskUsage")
    network_rx_kb: float = Field(alias="networkRxKb")
    network_tx_kb: float = Field(alias="networkTxKb")


class ServerNode(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    hostname: str
    ip_address: str = Field(alias="ipAddress")
    status: str
    last_seen: Optional[str] = Field(default=None, alias="lastSeen")
    metrics: Optional[SystemMetrics] = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)