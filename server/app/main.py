from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS
from app.core.database import init_db
from app.api.v1 import servers as servers_api
from app.api.v1 import alerts as alerts_api
from app.websockets import metrics_ws

app = FastAPI(title="Lynceus")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(servers_api.router, prefix="/api/v1")
app.include_router(alerts_api.router, prefix="/api/v1")
app.include_router(metrics_ws.router, prefix="/api/v1")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)