import os

DATABASE_URL = os.environ.get("LYNCEUS_DB_URL", "sqlite:///./lynceus.db")
CORS_ORIGINS = os.environ.get("LYNCEUS_CORS_ORIGINS", "*").split(",")
OFFLINE_THRESHOLD_SECONDS = int(os.environ.get("LYNCEUS_OFFLINE_THRESHOLD", "10"))