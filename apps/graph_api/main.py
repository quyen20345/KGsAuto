from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.graph_api import compare, entity, graph, health
from services.config import validate_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_settings("graph_api")
    yield


app = FastAPI(title="KGsAuto Graph API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(entity.router)
app.include_router(compare.router)
app.include_router(graph.router)
app.include_router(health.router, prefix="/api")
