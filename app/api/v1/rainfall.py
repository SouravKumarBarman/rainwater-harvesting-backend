from app.services.rainfallService import get_average_rainfall
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/average")
async def average_rainfall(
    latitude: float = Query(..., description="Location latitude"),
    longitude: float = Query(..., description="Location longitude"),
):
    """Return average annual rainfall (mm) for the last N years at a location.

    Uses the free Open-Meteo Archive API.
    """
    try:
        result = await get_average_rainfall(latitude, longitude, 5)
        return JSONResponse(content=result, status_code=200)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))