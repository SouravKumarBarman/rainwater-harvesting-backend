"""Live product pricing for rainwater harvesting estimates with price anomaly correction."""

from __future__ import annotations

import math
from dataclasses import dataclass
import httpx

from app.config import settings
from app.models.project_model import (
    CostEstimate,
    CostLineItem,
    HarvestResult,
    ProductOffer,
    RooftopInput,
)

SERPAPI_SEARCH_URL = "https://serpapi.com/search.json"

# --- Hardcoded Fallback/Baseline Constants ---
# Used when SerpAPI returns "per liter" unit pricing or anomalous accessory prices.
MIN_TANK_PRICE_PER_LITER = 4.5  # Dynamic baseline minimum (e.g., ₹4.50 per liter)


@dataclass(frozen=True)
class ProductRequirement:
    category: str
    query: str
    quantity: float
    unit: str
    target_capacity_liters: float | None = None  # Track volume for anomaly verification


async def estimate_project_cost(
    input_data: RooftopInput,
    harvest_result: HarvestResult,
) -> CostEstimate:
    # ── Guard: skip pricing entirely for infeasible projects ──────────────
    if not harvest_result.feasible:
        return CostEstimate(
            source="skipped",
            total=0,
            line_items=[],
            notes=[
                "Cost estimation skipped — project is not feasible. "
                "Address the feasibility issues before requesting a cost estimate. "
                f"Reasons: {'; '.join(harvest_result.feasibility_reasons)}"
            ],
        )

    requirements = _build_product_requirements(input_data, harvest_result)

    # ── No API key: return shell line items with no prices ────────────────
    if not settings.serpapi_api_key:
        return CostEstimate(
            source="unavailable",
            total=0,
            line_items=[
                CostLineItem(
                    category=item.category,
                    query=item.query,
                    quantity=item.quantity,
                    unit=item.unit,
                )
                for item in requirements
            ],
            notes=["Set SERPAPI_API_KEY to enable live Google Shopping prices."],
        )

    # ── Live pricing from Google Shopping via SerpAPI ─────────────────────
    line_items: list[CostLineItem] = []
    all_products: list[ProductOffer] = []
    notes: list[str] = []

    async with httpx.AsyncClient(timeout=30) as client:
        for item in requirements:
            try:
                offers = await _search_products(
                    client,
                    category=item.category,
                    query=item.query,
                    country=settings.shopping_country,
                    language=settings.shopping_language,
                )
            except httpx.HTTPStatusError as exc:
                offers = []
                notes.append(
                    f"SerpAPI returned HTTP {exc.response.status_code} "
                    f"for '{item.category}'."
                )
            except httpx.HTTPError:
                offers = []
                notes.append(f"Network error fetching prices for '{item.category}'.")

            selected = _select_offer(offers)
            unit_price = selected.extracted_price if selected else None
            
            # ── CRITICAL FIX: Detect and override "per-liter" or glitchy pricing ──
            if item.category == "storage_tank" and unit_price is not None and item.target_capacity_liters:
                estimated_floor_price = item.target_capacity_liters * MIN_TANK_PRICE_PER_LITER
                
                # If the API returned price is lower than the absolute floor price for this capacity
                if unit_price < estimated_floor_price:
                    # Case A: It's likely a "per liter" quote (e.g., ₹20/L)
                    if 1.0 <= unit_price <= 50.0:
                        corrected_price = unit_price * item.target_capacity_liters
                        notes.append(
                            f"Detected unit-rate pricing ({unit_price}/L) for storage tank. "
                            f"Extrapolated total unit price to {corrected_price}."
                        )
                        unit_price = corrected_price
                    # Case B: It's a completely wrong item/accessory (e.g., ₹150 cap)
                    else:
                        corrected_price = estimated_floor_price
                        notes.append(
                            f"Suspiciously low price ({unit_price}) for {item.target_capacity_liters}L tank. "
                            f"Fell back to baseline minimum estimation: {corrected_price}."
                        )
                        unit_price = corrected_price

            total_price = (
                round(unit_price * item.quantity, 2)
                if unit_price is not None
                else None
            )

            if total_price is None:
                notes.append(
                    f"No parseable price found for '{item.category}' "
                    f"(query: \"{item.query}\"). Excluded from total."
                )

            line_items.append(
                CostLineItem(
                    category=item.category,
                    query=item.query,
                    quantity=item.quantity,
                    unit=item.unit,
                    unit_price=unit_price,
                    total_price=total_price,
                    selected_product=selected,
                    alternative_products=offers,
                )
            )
            all_products.extend(offers)

    total = round(sum(item.total_price or 0 for item in line_items), 2)
    priced_count = sum(1 for item in line_items if item.total_price is not None)
    notes.insert(
        0,
        f"Live prices fetched for {priced_count}/{len(line_items)} line items "
        f"via Google Shopping (SerpAPI). Total may be partial.",
    )

    return CostEstimate(
        source="serpapi_google_shopping",
        total=total,
        line_items=line_items,
        products=all_products,
        notes=notes,
    )


# ── Product requirement builder ───────────────────────────────────────────────

def _build_product_requirements(
    input_data: RooftopInput,
    harvest_result: HarvestResult,
) -> list[ProductRequirement]:
    requirements: list[ProductRequirement] = []

    # 1. First-flush diverter
    roof_side_m = math.sqrt(input_data.roof_area_m2)
    num_downpipes = max(1, math.ceil(roof_side_m / 10))
    requirements.append(
        ProductRequirement(
            category="first_flush",
            query="rainwater first flush diverter kit",
            quantity=num_downpipes,
            unit="piece",
        )
    )

    # 2. Filter unit
    requirements.append(
        ProductRequirement(
            category="filter",
            query="rainwater harvesting filter unit mesh sand",
            quantity=num_downpipes,
            unit="piece",
        )
    )

    # 3. Gutters
    gutter_length_m = math.ceil(roof_side_m * 4)
    requirements.append(
        ProductRequirement(
            category="gutter",
            query="PVC rainwater gutter channel 3 meter",
            quantity=math.ceil(gutter_length_m / 3),
            unit="3 m length",
        )
    )

    # 4. Downpipes
    requirements.append(
        ProductRequirement(
            category="downpipe",
            query="PVC rainwater downpipe 3 meter 75mm",
            quantity=num_downpipes * 2,
            unit="3 m length",
        )
    )

    # 5. Storage tank
    if harvest_result.recommended_tank_volume_m3:
        tank_liters = (
            math.ceil(harvest_result.recommended_tank_volume_m3 * 1000 / 500) * 500
        )
        if tank_liters <= 5000:
            query = f"{tank_liters} litre water storage tank polyethylene"
        else:
            query = f"{tank_liters} litre underground sump water tank"
            
        requirements.append(
            ProductRequirement(
                category="storage_tank",
                query=query,
                quantity=1,
                unit="piece",
                target_capacity_liters=tank_liters,  # Passed for validation down the line
            )
        )

    # 6. Recharge pit materials
    if harvest_result.recharge_pit_details:
        pit = harvest_result.recharge_pit_details
        num_pits = pit.get("num_pits", 1)
        diameter = pit.get("diameter_m", 2.0)

        depth = pit.get("depth_m", 3.0)
        pipe_lengths = math.ceil(depth / 3) * num_pits
        requirements.append(
            ProductRequirement(
                category="recharge_casing_pipe",
                query=f"slotted PVC casing pipe {int(diameter * 1000)}mm rainwater recharge",
                quantity=pipe_lengths,
                unit="3 m length",
            )
        )

        gravel_bags = math.ceil(
            (math.pi * (diameter / 2) ** 2 * depth * 0.4 * 1600 / 25) * num_pits
        )
        requirements.append(
            ProductRequirement(
                category="recharge_gravel",
                query="coarse gravel filter media 25kg bag rainwater",
                quantity=gravel_bags,
                unit="25 kg bag",
            )
        )

        requirements.append(
            ProductRequirement(
                category="desilting_chamber",
                query="desilting chamber rainwater harvesting kit",
                quantity=num_pits,
                unit="piece",
            )
        )

    return requirements


# ── SerpAPI helpers ───────────────────────────────────────────────────────────

async def _search_products(
    client: httpx.AsyncClient,
    category: str,
    query: str,
    country: str = "in",
    language: str = "en",
) -> list[ProductOffer]:
    response = await client.get(
        SERPAPI_SEARCH_URL,
        params={
            "engine": "google_shopping",
            "q": query,
            "api_key": settings.serpapi_api_key,
            "gl": country,
            "hl": language,
            "num": 5,
        },
    )
    response.raise_for_status()
    payload = response.json()
    return [
        ProductOffer(
            title=item.get("title", "Untitled product"),
            source=item.get("source"),
            price=item.get("price"),
            extracted_price=item.get("extracted_price"),
            link=item.get("product_link") or item.get("link"),
            thumbnail=item.get("thumbnail"),
            rating=item.get("rating"),
            reviews=item.get("reviews"),
            category=category,
        )
        for item in payload.get("shopping_results", [])[:5]
    ]


def _select_offer(offers: list[ProductOffer]) -> ProductOffer | None:
    priced = [o for o in offers if o.extracted_price is not None]
    if not priced:
        return offers[0] if offers else None
    return min(priced, key=lambda o: o.extracted_price or 0)