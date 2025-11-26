"""Rainfall data service using Open-Meteo historical weather API."""

from datetime import date, timedelta
import httpx


async def get_average_rainfall(
    latitude: float,
    longitude: float,
    years: int,
) -> dict:
    """Return average annual rainfall (mm) for the last `years` years at the given location.

    Uses the free Open-Meteo Archive API (no API key required).
    https://open-meteo.com/en/docs/historical-weather-api

    Args:
        latitude: Location latitude.
        longitude: Location longitude.
        years: Number of past years to consider.

    Returns:
        A dict with yearly totals and the computed average, e.g.:
        {
            "latitude": 12.97,
            "longitude": 77.59,
            "years": 5,
            "yearly_totals_mm": {"2019": 900.2, "2020": 850.1, ...},
            "average_annual_rainfall_mm": 870.5
        }
    """
    today = date.today()
    # We take full calendar years ending last year (current year may be incomplete)
    end_year = today.year - 1
    start_year = end_year - years + 1

    start_date = date(start_year, 1, 1)
    end_date = date(end_year, 12, 31)

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": "precipitation_sum",
        "timezone": "auto",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    precip = daily.get("precipitation_sum", [])

    # Aggregate by year
    yearly_totals: dict[int, float] = {}
    for d, p in zip(dates, precip):
        if p is None:
            continue
        year = int(d[:4])
        yearly_totals[year] = yearly_totals.get(year, 0.0) + p

    # Round values
    yearly_totals = {y: round(v, 2) for y, v in sorted(yearly_totals.items())}

    if yearly_totals:
        average = round(sum(yearly_totals.values()) / len(yearly_totals), 2)
    else:
        average = 0.0

    return {
        "latitude": latitude,
        "longitude": longitude,
        "years": years,
        "yearly_totals_mm": {str(y): v for y, v in yearly_totals.items()},
        "average_annual_rainfall_mm": average,
    }
