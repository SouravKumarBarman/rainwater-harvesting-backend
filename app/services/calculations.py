import math
from app.models.project_model import RooftopInput, HarvestResult

ROOF_RUNOFF_COEFF = {
    "RCC": 0.85,
    "metal_sheet": 0.80,
    "tile": 0.75,
    "other": 0.70,
}

DAILY_DEMAND_LPCD = 70
MIN_ROOF_AREA_PER_PERSON = 10.0
RAINFALL_LOW = 300
RAINFALL_MARGINAL = 600
MIN_ROOF_AREA = 20.0


def _feasibility_check(
    roof_area: float,
    annual_rainfall_mm: float,
    num_occupants: int,
    harvestable_volume_m3: float,
) -> tuple[str, list[str]]:
    status = "feasible"
    reasons: list[str] = []

    if roof_area < MIN_ROOF_AREA:
        status = "infeasible"
        reasons.append(
            f"Roof area ({roof_area} m²) is below the minimum threshold of {MIN_ROOF_AREA} m²."
        )

    if annual_rainfall_mm < RAINFALL_LOW:
        status = "infeasible"
        reasons.append(
            f"Annual rainfall ({annual_rainfall_mm} mm) is critically low (< {RAINFALL_LOW} mm). "
            "RTRWH is not viable."
        )

    annual_demand_m3 = (num_occupants * DAILY_DEMAND_LPCD * 365) / 1000.0
    supply_ratio = harvestable_volume_m3 / annual_demand_m3 if annual_demand_m3 > 0 else 0

    if supply_ratio < 0.10 and status != "infeasible":
        status = "infeasible"
        reasons.append(
            f"Harvestable volume ({harvestable_volume_m3:.1f} m³/yr) covers only "
            f"{supply_ratio * 100:.1f}% of estimated annual non-potable demand "
            f"({annual_demand_m3:.1f} m³/yr) — not economically viable."
        )

    roof_per_person = roof_area / num_occupants if num_occupants > 0 else roof_area
    if roof_per_person < MIN_ROOF_AREA_PER_PERSON and status == "feasible":
        status = "marginal"
        reasons.append(
            f"Roof area per occupant ({roof_per_person:.1f} m²/person) is low "
            f"(recommended ≥ {MIN_ROOF_AREA_PER_PERSON} m²/person). "
            "System will only partially meet demand."
        )

    if RAINFALL_LOW <= annual_rainfall_mm < RAINFALL_MARGINAL and status == "feasible":
        status = "marginal"
        reasons.append(
            f"Annual rainfall ({annual_rainfall_mm} mm) is marginal "
            f"({RAINFALL_LOW}–{RAINFALL_MARGINAL} mm). "
            "Consider a hybrid system with supplemental sources."
        )

    if 0.10 <= supply_ratio < 0.25 and status == "feasible":
        status = "marginal"
        reasons.append(
            f"Harvest covers only {supply_ratio * 100:.1f}% of annual demand. "
            "System will provide limited benefit."
        )

    if status == "feasible":
        reasons.append(
            f"Roof area, rainfall, and occupancy are all adequate for RTRWH. "
            f"Expected to cover {min(supply_ratio * 100, 100):.0f}% of annual "
            f"non-potable demand ({annual_demand_m3:.1f} m³/yr)."
        )

    return status, reasons


def _size_tank(
    harvestable_volume_m3: float,
    num_occupants: int,
    annual_rainfall_mm: float,
) -> float:
    daily_demand_m3 = (num_occupants * DAILY_DEMAND_LPCD) / 1000.0

    if annual_rainfall_mm >= 1500:
        dry_spell_days = 20
    elif annual_rainfall_mm >= 900:
        dry_spell_days = 30
    elif annual_rainfall_mm >= 600:
        dry_spell_days = 45
    else:
        dry_spell_days = 60

    demand_buffer_m3 = daily_demand_m3 * dry_spell_days
    max_tank = 0.50 * harvestable_volume_m3
    min_tank = daily_demand_m3 * 7

    return round(min(max(demand_buffer_m3, min_tank), max_tank), 2)


def _size_recharge_pit(harvestable_volume_m3: float) -> dict:
    target_pit_volume = max(0.10 * harvestable_volume_m3, 9.0)
    depth = 3.0
    radius = math.sqrt(target_pit_volume / (math.pi * depth))
    diameter = round(radius * 2, 1)

    num_pits = 1
    if diameter > 3.0:
        num_pits = math.ceil(target_pit_volume / (math.pi * 1.5**2 * depth))
        diameter = 3.0

    actual_volume = round(num_pits * math.pi * (diameter / 2) ** 2 * depth, 2)

    return {
        "num_pits": num_pits,
        "diameter_m": diameter,
        "depth_m": depth,
        "volume_m3": actual_volume,
        "note": (
            f"{num_pits} pit(s) of {diameter} m diameter × {depth} m depth. "
            "Refine dimensions after soil percolation tests (IS 3025 / BIS)."
        ),
    }


def calculate_harvest(input_data: RooftopInput) -> HarvestResult:
    # 1. Runoff coefficient
    C = ROOF_RUNOFF_COEFF.get(input_data.roof_type, 0.70)

    # 2. Rainfall: mm → m
    R_m = input_data.annual_rainfall_mm / 1000.0

    # 3. Harvestable volume (m³/year)
    V = round(input_data.roof_area_m2 * R_m * C, 2)

    # 4. Feasibility
    status, reasons = _feasibility_check(
        roof_area=input_data.roof_area_m2,
        annual_rainfall_mm=input_data.annual_rainfall_mm,
        num_occupants=input_data.num_occupants,
        harvestable_volume_m3=V,
    )
    feasible = status in ("feasible", "marginal")

    # 5. Tank sizing (only if feasible)
    recommended_tank = None
    if input_data.system_type in ("storage", "hybrid") and feasible:
        recommended_tank = _size_tank(
            harvestable_volume_m3=V,
            num_occupants=input_data.num_occupants,
            annual_rainfall_mm=input_data.annual_rainfall_mm,
        )

    # 6. Recharge pit sizing (only if feasible)
    recharge_details = None
    if input_data.system_type in ("recharge", "hybrid") and feasible:
        recharge_details = _size_recharge_pit(V)

    # 7. Guidelines
    guidelines = [
        "Install a first-flush diverter (min. 25 L per 100 m² of roof).",
        "Use a multi-stage filter: mesh screen → gravel → sand → activated charcoal.",
        "Inspect and clean gutters, downpipes, and filters before each monsoon.",
        "Ensure overflow is directed ≥ 2 m away from the building foundation.",
        "Label harvested water tanks clearly — NOT FOR DRINKING unless treated.",
    ]
    if input_data.system_type in ("recharge", "hybrid"):
        guidelines += [
            "Recharge pit must be ≥ 10 m from any septic tank or soak pit.",
            "Conduct percolation test (IS 2720 Part 17) before finalising pit depth.",
            "Provide a desilting chamber upstream of the recharge pit.",
        ]
    if status == "marginal":
        guidelines.append(
            "⚠ System is marginal — consider supplementing with municipal supply "
            "or increasing roof catchment area if possible."
        )

    # 8. estimated_cost is intentionally 0 here.
    #    The real cost comes from estimate_project_cost() in pricing_service.py
    #    which fetches live prices from Google Shopping via SerpAPI.
    return HarvestResult(
        feasible=feasible,
        feasibility_reasons=reasons,
        harvestable_volume_m3=V,
        recommended_tank_volume_m3=recommended_tank,
        recharge_pit_details=recharge_details,
        estimated_cost=0,
        guidelines=guidelines,
    )