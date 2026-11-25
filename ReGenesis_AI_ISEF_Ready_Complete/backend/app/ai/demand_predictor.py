from typing import List, Dict, Any

class DemandPredictor:
    """Descriptive snapshot of current listings; not a time-series forecast."""

    @classmethod
    def predict(cls, active_listings: List[Dict[str, Any]]) -> Dict[str, Any]:
        supply: Dict[str, float] = {}
        demand: Dict[str, float] = {}
        for row in active_listings:
            category = str(row.get("category") or "غير مصنف")
            trade = str(row.get("trade_type") or row.get("tradeType") or "")
            quantity = max(0.0, float(row.get("quantity") or row.get("qty") or 0.0))
            if "عرض" in trade or "supply" in trade.lower() or "offer" in trade.lower():
                supply[category] = supply.get(category, 0.0) + quantity
            elif "طلب" in trade or "demand" in trade.lower():
                demand[category] = demand.get(category, 0.0) + quantity
        categories = sorted(set(supply) | set(demand))
        predictions = []
        for category in categories:
            s = round(supply.get(category, 0.0), 3)
            d = round(demand.get(category, 0.0), 3)
            if d > s:
                trend = "Demand exceeds listed supply"
                recommendation = "Potential supply gap in current listings; confirm buyer specifications and contact the listed parties."
            elif s > d:
                trend = "Listed supply exceeds demand"
                recommendation = "Potential surplus in current listings; seek additional buyers and verify material quality."
            else:
                trend = "Balanced or no recorded volume"
                recommendation = "Review listing freshness and confirm whether additional supply or demand exists."
            predictions.append({
                "material_category": category, "trend": trend,
                "confidence_level": "Descriptive snapshot only; no validated historical forecast",
                "active_demand_tons": d, "active_supply_tons": s,
                "price_outlook": "Unavailable: no verified time-series price data",
                "recommendation": recommendation
            })
        return {
            "status": "active" if active_listings else "insufficient_data",
            "historical_data_sufficiency": "No historical time-series data available; snapshot only",
            "predictions": predictions,
            "notes": "This compares currently registered supply and demand listings only. It is not a market forecast and does not verify availability or transactions."
        }
