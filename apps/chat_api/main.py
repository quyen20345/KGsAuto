from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from apps.chat_api.schemas import (
    ChatHealthResponse,
    ChatModesResponse,
    ChatQueryRequest,
    ChatQueryResponse,
    OpenAIChatCompletionRequest,
    OpenAIModel,
    OpenAIModelsResponse,
)
from apps.chat_api.service import (
    DEFAULT_MODE,
    SUPPORTED_MODES,
    openai_completion_response,
    openai_stream_events,
    query_chat,
    query_openai_compatible,
)
from services.config import validate_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_settings("rag")
    yield


app = FastAPI(title="KGsAuto Chat API", version="0.1.0", lifespan=lifespan)

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


@app.get("/v1/models", response_model=OpenAIModelsResponse)
def openai_models() -> OpenAIModelsResponse:
    """OpenAI-compatible model list for reusable chat UIs."""

    return OpenAIModelsResponse(data=[OpenAIModel(id=mode) for mode in SUPPORTED_MODES])


@app.post("/v1/chat/completions")
async def openai_chat_completions(req: OpenAIChatCompletionRequest):
    """OpenAI-compatible adapter over KGsAuto RAG chat.

    This lets external UIs such as chatbot-ui talk to KGsAuto by setting their
    OpenAI base URL to the chat_api server.
    """

    try:
        if req.stream:
            return StreamingResponse(openai_stream_events(req), media_type="text/event-stream")
        chat = await query_openai_compatible(req)
        return openai_completion_response(req, chat)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
