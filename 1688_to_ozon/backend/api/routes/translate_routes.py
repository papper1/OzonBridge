from fastapi import APIRouter

from ..schemas.product_schema import TranslateRequest, TranslateResponse
from ..services.translate_service import translate_products


router = APIRouter(tags=["translate"])


@router.post("/translate", response_model=TranslateResponse)
def translate(request: TranslateRequest) -> TranslateResponse:
    return TranslateResponse(items=translate_products(request.products))

