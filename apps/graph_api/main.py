from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.graph_api import entity, graph, health

app = FastAPI(title="KGsAuto Graph API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(entity.router)
app.include_router(graph.router)
app.include_router(health.router, prefix="/api")
