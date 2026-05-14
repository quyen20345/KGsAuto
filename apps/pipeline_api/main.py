from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.pipeline_api.routes import crawl, events, files, pipeline
from services.config import validate_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_settings("pipeline_api")
    yield


app = FastAPI(title="KGsAuto Pipeline API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(files.router)
app.include_router(pipeline.router)
app.include_router(events.router)
app.include_router(crawl.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "pipeline_api"}
