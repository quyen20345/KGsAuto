from fastapi import APIRouter, HTTPException

from apps.pipeline_api.config import RAW_DIR
from apps.pipeline_api.models import CrawlRequest, CrawlResponse

router = APIRouter(prefix="/api", tags=["crawl"])


@router.post("/crawl")
async def crawl_urls_endpoint(request: CrawlRequest) -> CrawlResponse:
    if not request.urls:
        raise HTTPException(status_code=400, detail="No URLs provided")

    import asyncio
    from services.crawler.crawl_lib import crawl_urls

    files_created, errors = await asyncio.to_thread(crawl_urls, request.urls, RAW_DIR)
    return CrawlResponse(files_created=files_created, errors=errors)
