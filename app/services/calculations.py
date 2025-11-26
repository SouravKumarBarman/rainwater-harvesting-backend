from app.models.project_model import RooftopInput, HarvestResult

ROOF_RUNOFF_COEFF = {
    "RCC": 0.85,
    "metal_sheet": 0.80,
    "tile": 0.75,
    "other": 0.70,
}

COST_PER_M3_TANK = 3000  # rupees per m3 (example, tune later)
COST_PER_M3_RECHARGE = 1500
FIXED_INSTALLATION_COST = 5000

def calculate_harvest(input_data: RooftopInput) -> HarvestResult:
    # 1. Runoff coefficient
    C = ROOF_RUNOFF_COEFF.get(input_data.roof_type, 0.7)

    # 2. Annual rainfall: mm -> m
    R_m = input_data.annual_rainfall_mm / 1000.0

    # 3. Harvestable volume (m3)
    V = input_data.roof_area_m2 * R_m * C

    feasible = True
    reasons: list[str] = []

    if input_data.roof_area_m2 < 20:
        feasible = False
        reasons.append("Roof area is less than 20 m².")
    if input_data.annual_rainfall_mm < 300:
        feasible = False
        reasons.append("Annual rainfall is very low (< 300 mm).")

    if feasible:
        reasons.append("Rooftop area and rainfall are adequate for RTRWH.")

    # 4. Tank sizing for storage system
    recommended_tank = None
    recharge_details = None

    # Simple domestic demand assumption
    # 70 L per person per day for non-potable uses
    daily_demand_m3 = (input_data.num_occupants * 70) / 1000.0
    demand_30_days = daily_demand_m3 * 30

    if input_data.system_type in ("storage", "hybrid"):
        recommended_tank = min(0.25 * V, demand_30_days)

    # 5. Recharge pit sizing (very simplified)
    if input_data.system_type in ("recharge", "hybrid"):
        # assume one pit, diameter 2m, depth 3m
        import math
        diameter = 2.0
        depth = 3.0
        pit_volume = math.pi * (diameter / 2) ** 2 * depth
        recharge_details = {
            "diameter_m": diameter,
            "depth_m": depth,
            "volume_m3": pit_volume,
            "note": "Dimensions can be refined based on soil percolation tests."
        }

    # 6. Cost estimation
    cost = FIXED_INSTALLATION_COST

    if recommended_tank:
        cost += recommended_tank * COST_PER_M3_TANK
    if recharge_details:
        cost += recharge_details["volume_m3"] * COST_PER_M3_RECHARGE

    # 7. Guidelines
    guidelines = [
        "Provide first-flush arrangement and filtration unit.",
        "Clean the rooftop and gutters before monsoon.",
        "Ensure overflow is directed safely away from building foundation.",
    ]
    if input_data.system_type in ("recharge", "hybrid"):
        guidelines.append("Recharge pit should be at least 10 m away from septic tanks.")

    return HarvestResult(
        feasible=feasible,
        feasibility_reasons=reasons,
        harvestable_volume_m3=round(V, 2),
        recommended_tank_volume_m3=(
            round(recommended_tank, 2) if recommended_tank else None
        ),
        recharge_pit_details=recharge_details,
        estimated_cost=round(cost, 2),
        guidelines=guidelines,
    )
