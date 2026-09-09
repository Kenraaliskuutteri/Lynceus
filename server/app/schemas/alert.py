from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AlertEventOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    server_id: str = Field(alias="serverId")
    metric: str
    value: float
    threshold: float
    status: str
    triggered_at: str = Field(alias="triggeredAt")
    resolved_at: Optional[str] = Field(default=None, alias="resolvedAt")