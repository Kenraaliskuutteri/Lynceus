import os

DATABASE_URL = os.environ.get("LYNCEUS_DB_URL", "sqlite:///./lynceus.db")
CORS_ORIGINS = os.environ.get("LYNCEUS_CORS_ORIGINS", "*").split(",")
OFFLINE_THRESHOLD_SECONDS = int(os.environ.get("LYNCEUS_OFFLINE_THRESHOLD", "10"))

ALERT_THRESHOLDS = {
    "cpu_usage": float(os.environ.get("LYNCEUS_CPU_THRESHOLD", "90")),
    "ram_usage": float(os.environ.get("LYNCEUS_RAM_THRESHOLD", "90")),
    "disk_usage": float(os.environ.get("LYNCEUS_DISK_THRESHOLD", "90")),
}

WEBHOOK_URL = os.environ.get("LYNCEUS_WEBHOOK_URL", "").strip()
WEBHOOK_FORMAT = os.environ.get("LYNCEUS_WEBHOOK_FORMAT", "auto").strip().lower()