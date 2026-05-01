"""Live product pricing for rainwater harvesting estimates."""

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


@dataclass(frozen=True)
class ProductRequirement:
    category: str
    query: str
    quantity: float
    unit: str


async def estimate_project_cost(
    input_data: RooftopInput,
    harvest_result: HarvestResult,
) -> CostEstimate:
    requirements = _build_product_requirements(input_data, harvest_result)
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
            notes=["Set SERPAPI_API_KEY to enable live shopping prices."],
        )

    line_items: list[CostLineItem] = []
    all_products: list[ProductOffer] = []
    notes: list[str] = []

    async with httpx.AsyncClient(timeout=30) as client:
        for item in requirements:
            try:
                offers = await _search_products(client, item.category, item.query)
            except httpx.HTTPError:
                offers = []
                notes.append(f"Could not fetch live products for {item.category}.")
            selected = _select_offer(offers)
            total_price = (
                round(selected.extracted_price * item.quantity, 2)
                if selected and selected.extracted_price is not None
                else None
            )
            line_items.append(
                CostLineItem(
                    category=item.category,
                    query=item.query,
                    quantity=item.quantity,
                    unit=item.unit,
                    unit_price=selected.extracted_price if selected else None,
                    total_price=total_price,
                    selected_product=selected,
                )
            )
            all_products.extend(offers)

    total = round(
        sum(item.total_price or 0 for item in line_items),
        2,
    )
    if any(item.total_price is None for item in line_items):
        notes.append("Some products did not include parseable prices.")

    return CostEstimate(
        source="serpapi_google_shopping",
        total=total,
        line_items=line_items,
        products=all_products,
        notes=notes,
    )


def _build_product_requirements(
    input_data: RooftopInput,
    harvest_result: HarvestResult,
) -> list[ProductRequirement]:
    requirements = [
        ProductRequirement(
            category="filter",
            query="rainwater harvesting filter",
            quantity=1,
            unit="piece",
        ),
        ProductRequirement(
            category="first_flush",
            query="rainwater first flush diverter kit",
            quantity=1,
            unit="piece",
        ),
    ]

    roof_side_m = math.sqrt(input_data.roof_area_m2)
    gutter_length_m = max(3, math.ceil(roof_side_m * 4))
    requirements.append(
        ProductRequirement(
            category="gutter",
            query="PVC rainwater gutter pipe 3 meter",
            quantity=math.ceil(gutter_length_m / 3),
            unit="3 meter length",
        )
    )

    if harvest_result.recommended_tank_volume_m3:
        tank_liters = (
            math.ceil(harvest_result.recommended_tank_volume_m3 * 1000 / 100) * 100
        )
        requirements.append(
            ProductRequirement(
                category="storage_tank",
                query=f"{tank_liters} litre water storage tank",
                quantity=1,
                unit="piece",
            )
        )

    if input_data.system_type in ("recharge", "hybrid"):
        requirements.append(
            ProductRequirement(
                category="recharge_material",
                query="rainwater harvesting recharge pit kit",
                quantity=1,
                unit="set",
            )
        )

    return requirements


async def _search_products(
    client: httpx.AsyncClient,
    category: str,
    query: str,
) -> list[ProductOffer]:
    response = await client.get(
        SERPAPI_SEARCH_URL,
        params={
            "engine": "google_shopping",
            "q": query,
            "api_key": settings.serpapi_api_key,
            "gl": settings.shopping_country,
            "hl": settings.shopping_language,
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
    priced_offers = [offer for offer in offers if offer.extracted_price is not None]
    if not priced_offers:
        return offers[0] if offers else None
    return min(priced_offers, key=lambda offer: offer.extracted_price or 0)
