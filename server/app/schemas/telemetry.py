# I love how i named this folder. I'm something of a practical joker my self.
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


class ServerThresholds(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cpu_usage: float = Field(alias="cpuUsage")
    ram_usage: float = Field(alias="ramUsage")
    disk_usage: float = Field(alias="diskUsage")
    offline_seconds: int = Field(alias="offlineSeconds")


class ServerThresholdsUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cpu_usage: Optional[float] = Field(default=None, alias="cpuUsage")
    ram_usage: Optional[float] = Field(default=None, alias="ramUsage")
    disk_usage: Optional[float] = Field(default=None, alias="diskUsage")
    offline_seconds: Optional[int] = Field(default=None, alias="offlineSeconds")
    clear: list[str] = Field(default_factory=list)


class ServerNode(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    hostname: str
    ip_address: str = Field(alias="ipAddress")
    status: str
    last_seen: Optional[str] = Field(default=None, alias="lastSeen")
    metrics: Optional[SystemMetrics] = None
    thresholds: ServerThresholds


class ServerUptime(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    uptime_percent: float = Field(alias="uptimePercent")
    downtime_seconds: float = Field(alias="downtimeSeconds")
    incident_count: int = Field(alias="incidentCount")
    window_days: int = Field(alias="windowDays")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)