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


class ProductOffer(BaseModel):
    title: str
    source: str | None = None
    price: str | None = None
    extracted_price: float | None = None
    currency: str = "INR"
    link: str | None = None
    thumbnail: str | None = None
    rating: float | None = None
    reviews: int | None = None
    category: str


class CostLineItem(BaseModel):
    category: str
    query: str
    quantity: float
    unit: str
    unit_price: float | None = None
    total_price: float | None = None
    selected_product: ProductOffer | None = None


class CostEstimate(BaseModel):
    source: Literal["serpapi_google_shopping", "unavailable"]
    currency: str = "INR"
    total: float
    line_items: list[CostLineItem] = Field(default_factory=list)
    products: list[ProductOffer] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class HarvestResult(BaseModel):
    feasible: bool
    feasibility_reasons: list[str]
    harvestable_volume_m3: float
    recommended_tank_volume_m3: float | None = None
    recharge_pit_details: dict | None = None
    estimated_cost: float
    cost_estimate: CostEstimate | None = None
    products: list[ProductOffer] = Field(default_factory=list)
    guidelines: list[str]


class ProjectCreate(BaseModel):
    input: RooftopInput


class Project(BaseModel):
    id: str = Field(alias="_id")
    user_id: str
    input: RooftopInput
    result: HarvestResult
    created_at: datetime
