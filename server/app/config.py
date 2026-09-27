import os

API_KEY = os.environ.get("LYNCEUS_API_KEY", "").strip()
DATABASE_URL = os.environ.get("LYNCEUS_DB_URL", "sqlite:///./lynceus.db")
CORS_ORIGINS = os.environ.get("LYNCEUS_CORS_ORIGINS", "*").split(",")
OFFLINE_THRESHOLD_SECONDS = int(os.environ.get("LYNCEUS_OFFLINE_THRESHOLD", "10"))
ACK_EXPIRY_HOURS = float(os.environ.get("LYNCEUS_ACK_EXPIRY_HOURS", "0"))
ALERT_HYSTERESIS_PERCENT = float(os.environ.get("LYNCEUS_ALERT_HYSTERESIS_PERCENT", "5"))

JWT_SECRET = os.environ.get("LYNCEUS_JWT_SECRET", "").strip()
JWT_ACCESS_MINUTES = int(os.environ.get("LYNCEUS_JWT_ACCESS_MINUTES", "15"))
JWT_REFRESH_DAYS = int(os.environ.get("LYNCEUS_JWT_REFRESH_DAYS", "7"))
LOGIN_MAX_ATTEMPTS = int(os.environ.get("LYNCEUS_LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_LOCKOUT_MINUTES = int(os.environ.get("LYNCEUS_LOGIN_LOCKOUT_MINUTES", "15"))
ADMIN_BOOTSTRAP_USERNAME = os.environ.get("LYNCEUS_ADMIN_USERNAME", "").strip()
ADMIN_BOOTSTRAP_PASSWORD = os.environ.get("LYNCEUS_ADMIN_PASSWORD", "").strip()

ALERT_THRESHOLDS = {
    "cpu_usage": float(os.environ.get("LYNCEUS_CPU_THRESHOLD", "90")),
    "ram_usage": float(os.environ.get("LYNCEUS_RAM_THRESHOLD", "90")),
    "disk_usage": float(os.environ.get("LYNCEUS_DISK_THRESHOLD", "90")),
}

WEBHOOK_URL = os.environ.get("LYNCEUS_WEBHOOK_URL", "").strip()
WEBHOOK_FORMAT = os.environ.get("LYNCEUS_WEBHOOK_FORMAT", "auto").strip().lower()