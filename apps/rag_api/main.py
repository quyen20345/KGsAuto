from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from services.rag_system import RAGConfig, UnifiedRetrievalPipeline


app = FastAPI(title="RAG API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


ALLOWED_MODES = {"semantic_search", "graph_search", "naive_grag", "hybrid"}
_pipeline = None


def get_pipeline() -> UnifiedRetrievalPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = UnifiedRetrievalPipeline(RAGConfig())
    return _pipeline


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    mode: str = "semantic_search"
    top_k: int = Field(default=5, ge=1, le=20)
    include_evidence: bool = False


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "unified_retrieval_api", "modes": sorted(ALLOWED_MODES)}


@app.post("/query")
async def query(req: QueryRequest) -> dict:
    mode = req.mode.strip()
    if mode not in ALLOWED_MODES:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}")

    try:
        return await get_pipeline().aquery(
            question=req.question,
            mode=mode,
            top_k=req.top_k,
            include_evidence=req.include_evidence,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
