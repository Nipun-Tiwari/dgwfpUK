from fastapi import APIRouter

from ..repository import is_data_loaded
from ..schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health():
    data_loaded = is_data_loaded()
    return HealthResponse(status="ok" if data_loaded else "degraded", dataLoaded=data_loaded)
