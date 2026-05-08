from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from apps.chat_api.schemas import ChatHealthResponse, ChatModesResponse, ChatQueryRequest, ChatQueryResponse
from apps.chat_api.service import DEFAULT_MODE, SUPPORTED_MODES, query_chat


app = FastAPI(title="KGsAuto Chat API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=ChatHealthResponse)
def health() -> ChatHealthResponse:
    return ChatHealthResponse(status="ok", service="chat_api", modes=list(SUPPORTED_MODES))


@app.get("/modes", response_model=ChatModesResponse)
def modes() -> ChatModesResponse:
    return ChatModesResponse(modes=list(SUPPORTED_MODES), default_mode=DEFAULT_MODE)


@app.post("/query", response_model=ChatQueryResponse)
async def query(req: ChatQueryRequest) -> ChatQueryResponse:
    try:
        return await query_chat(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
