from pydantic import BaseModel, Field
from datetime import datetime
from typing import Literal, Optional

class RooftopInput(BaseModel):
    location: str
    roof_area_m2: float = Field(gt=0)
    roof_type: Literal["RCC", "metal_sheet", "tile", "other"]
    annual_rainfall_mm: float = Field(gt=0)
    use_type: Literal["domestic", "institutional", "industrial"] = "domestic"
    num_occupants: int = Field(gt=0)
    system_type: Literal["storage", "recharge", "hybrid"] = "storage"
    soil_type: Optional[Literal["sand", "loam", "clay"]] = None

class HarvestResult(BaseModel):
    feasible: bool
    feasibility_reasons: list[str]
    harvestable_volume_m3: float
    recommended_tank_volume_m3: float | None = None
    recharge_pit_details: dict | None = None
    estimated_cost: float
    guidelines: list[str]

class ProjectCreate(BaseModel):
    input: RooftopInput

class Project(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    input: RooftopInput
    result: HarvestResult
    created_at: datetime
