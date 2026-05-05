from fastapi import APIRouter, HTTPException

from ..schemas.crawl_schema import (
    CrawlAcceptedResponse,
    CrawlRequest,
    CrawlResultResponse,
    CrawlStatusResponse,
)
from ..services.crawl_service import get_job_result, get_job_status, submit_crawl_job


router = APIRouter(tags=["crawl"])


@router.post("/crawl", response_model=CrawlAcceptedResponse)
def create_crawl_job(request: CrawlRequest) -> CrawlAcceptedResponse:
    record = submit_crawl_job(request)
    return CrawlAcceptedResponse(
        job_id=record["job_id"],
        status=record["status"],
        message=record["message"],
    )


@router.get("/crawl/status/{job_id}", response_model=CrawlStatusResponse)
def crawl_status(job_id: str) -> CrawlStatusResponse:
    record = get_job_status(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return CrawlStatusResponse(**record)


@router.get("/crawl/result/{job_id}", response_model=CrawlResultResponse)
def crawl_result(job_id: str) -> CrawlResultResponse:
    result = get_job_result(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return CrawlResultResponse(**result)

