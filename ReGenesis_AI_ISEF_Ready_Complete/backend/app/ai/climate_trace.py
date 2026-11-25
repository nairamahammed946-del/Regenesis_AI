"""Read-only client for Climate TRACE's public beta API.

These are emissions-source / asset records, not a verified B2B factory directory.
The API is beta; keep request volume low and preserve source attribution.
"""
from typing import Any, Dict, List
import httpx

BASE = "https://api.climatetrace.org/v7"

async def search_industrial_assets(country_code: str = "EGY", sector: str = "manufacturing", year: int = 2025, limit: int = 25) -> Dict[str, Any]:
    country_code = (country_code or "EGY").strip().upper()
    sector = (sector or "manufacturing").strip().lower()
    limit = max(1, min(int(limit), 100))
    params = {"year": year, "gas": "co2e_100yr", "sectors": sector,
              "gadmId": country_code, "limit": limit, "offset": 0}
    async with httpx.AsyncClient(timeout=httpx.Timeout(15), follow_redirects=True) as client:
        response = await client.get(f"{BASE}/sources", params=params)
        response.raise_for_status()
        payload = response.json()
    rows = payload if isinstance(payload, list) else payload.get("results", [])
    assets: List[Dict[str, Any]] = []
    for row in rows[:limit]:
        source_id = row.get("id")
        assets.append({
            "source_id": source_id,
            "name": row.get("name"),
            "country": row.get("country"),
            "sector": row.get("sector"),
            "subsector": row.get("subsector"),
            "asset_type": row.get("assetType"),
            "capacity": row.get("capacity"),
            "capacity_units": row.get("capacityUnits"),
            "annual_co2e_estimate": row.get("emissionsQuantity"),
            "emissions_gas": row.get("gas"),
            "year": row.get("year"),
            "latitude": (row.get("centroid") or {}).get("latitude"),
            "longitude": (row.get("centroid") or {}).get("longitude"),
            "source_url": f"https://api.climatetrace.org/v7/sources/{source_id}" if source_id is not None else "https://climatetrace.org/data",
            "data_kind": "public emissions asset record; not factory verification or waste-supply data"
        })
    return {"count": len(assets), "assets": assets,
            "source": "Climate TRACE API v7 (beta)",
            "license": "CC BY 4.0 - attribution required; confirm current terms",
            "notice": "These are emissions-source asset records. They do not establish current operation, contact details, waste generation, purchasing demand, or willingness to transact."}
