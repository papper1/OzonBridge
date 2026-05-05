from fastapi import APIRouter

from ..schemas.product_schema import MapToOzonRequest, MapToOzonResponse
from ..services.mapping_service import map_products_to_ozon


router = APIRouter(tags=["mapping"])


@router.post("/map-to-ozon", response_model=MapToOzonResponse)
def map_to_ozon(request: MapToOzonRequest) -> MapToOzonResponse:
    return MapToOzonResponse(items=map_products_to_ozon(request.products))

