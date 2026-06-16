"""Rainfall service using IMD gridded data via imdlib — matches IMD official figures."""

import logging
import imdlib as imd
import numpy as np
from pathlib import Path
from datetime import date

logger = logging.getLogger(__name__)

# Place downloaded IMD files inside the project to keep repository-contained caches
# e.g., <repo_root>/data/imd_rainfall
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data" / "imd_rainfall"


async def get_average_rainfall(
    latitude: float,
    longitude: float,
    years: int,
) -> dict:
    """Return yearly totals and average annual rainfall (mm) for a location.

    This function is defensive about time selection — it slices each calendar
    year range explicitly and skips years with no data instead of assuming a
    single label like "1970" exists in the time coordinate.
    """
    try:
        today = date.today()
        end_year = today.year - 1
        start_year = end_year - years + 1

        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Download IMD gridded rainfall data (downloads .grd files from IMD Pune)
        data = imd.get_data(
            var_type="rain",
            start_yr=start_year,
            end_yr=end_year,
            fn_format="yearwise",
            file_dir=str(DATA_DIR),
        )

        # `imd.get_data` returns an IMD object (with `get_xarray()` helper).
        if hasattr(data, "get_xarray"):
            xr_data = data.get_xarray()
        else:
            xr_data = data

        yearly_totals: dict[int, float] = {}
        for year in range(start_year, end_year + 1):
            # slice to the calendar year to avoid selection issues across datasets
            yr_data = xr_data.sel(time=slice(f"{year}-01-01", f"{year}-12-31"))
            if getattr(yr_data, "sizes", {}).get("time", 0) == 0:
                logger.debug("No data for year %s at requested range", year)
                continue

            # Find nearest grid point to requested lat/lon
            nearest = yr_data.sel(lat=latitude, lon=longitude, method="nearest")
            rain_vals = nearest["rain"].values
            # IMD uses negative or sentinel values for missing values (e.g., -999)
            valid = rain_vals[(rain_vals > 0) & np.isfinite(rain_vals)]
            yearly_totals[year] = round(float(valid.sum()) if valid.size > 0 else 0.0, 2)

        average = (
            round(sum(yearly_totals.values()) / len(yearly_totals), 2)
            if yearly_totals
            else 0.0
        )

        return {
            "latitude": latitude,
            "longitude": longitude,
            "years": years,
            "source": "IMD 0.25° gridded (imdlib)",
            "yearly_totals_mm": {str(y): v for y, v in sorted(yearly_totals.items())},
            "average_annual_rainfall_mm": average,
        }
    except Exception:
        logger.exception("Failed computing average rainfall for %s,%s", latitude, longitude)
        raise