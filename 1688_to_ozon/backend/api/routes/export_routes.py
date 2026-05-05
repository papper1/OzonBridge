from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..schemas.product_schema import ExportRequest, ExportResponse
from ..services.export_service import export_products
from ..services.runtime_store import runtime_store


router = APIRouter(tags=["export"])


@router.post("/export", response_model=ExportResponse)
def export(request: ExportRequest) -> ExportResponse:
    payload = export_products(request.products, request.file_name)
    return ExportResponse(**payload)


@router.get("/download/{file_id}")
def download(file_id: str) -> FileResponse:
    file_path = runtime_store.get_file(file_id)
    if file_path is None:
        raise HTTPException(status_code=404, detail="File not found")
    resolved_path = Path(file_path)
    if not resolved_path.is_file():
        raise HTTPException(status_code=404, detail="File path is missing")
    return FileResponse(
        path=resolved_path,
        filename=resolved_path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

