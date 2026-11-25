from sqlalchemy import select, func
from backend.app.models.waste import WasteListing
from backend.app.models.user import Factory
from backend.app.models.matching import MatchEvent
from backend.app.models.marketplace import PurchaseRequest, Order
from backend.app.schemas.dashboard import DashboardKPIs, DashboardAnalyticsResponse, CategoryChartItem, TrendChartItem


class DashboardService:
    @staticmethod
    def get_analytics(db):
        listings = db.execute(select(WasteListing).where(WasteListing.status == "Active")).scalars().all()
        offers = [x for x in listings if "عرض" in (x.trade_type or "")]
        total_tonnage = sum(float(x.quantity or 0) for x in offers)

        factories_count = db.execute(select(func.count(Factory.id))).scalar() or 0
        potential_matches = db.execute(select(func.count(MatchEvent.id))).scalar() or 0
        pending_requests = db.execute(
            select(func.count(PurchaseRequest.id)).where(PurchaseRequest.status.in_(["Pending", "New", "Submitted"]))
        ).scalar() or 0
        completed_orders = db.execute(
            select(func.count(Order.id)).where(Order.status.in_(["Completed", "Delivered"]))
        ).scalar() or 0
        completed = db.execute(
            select(Order).where(Order.status.in_(["Completed", "Delivered"]))
        ).scalars().all()
        reused_tons = sum(float(order.quantity or 0) for order in completed)

        # No verified lifecycle/carbon methodology is bundled; do not invent avoided-emissions totals.
        co2_avoided = 0.0

        kpis = DashboardKPIs(
            total_waste_registered_tons=round(total_tonnage, 2),
            total_active_listings=len(listings),
            active_factories_count=int(factories_count),
            successful_matches_count=int(potential_matches),
            pending_purchase_requests=int(pending_requests),
            completed_orders_count=int(completed_orders),
            estimated_waste_reused_tons=round(reused_tons, 2),
            estimated_co2_avoided_tons=round(co2_avoided, 2),
            estimated_economic_savings_usd=0.0,
        )

        category_counts = {}
        for listing in offers:
            category_counts[listing.category] = category_counts.get(listing.category, 0.0) + float(listing.quantity or 0)
        total = sum(category_counts.values()) or 1.0
        color_map = {
            "خشب": "#22c55e", "بلاستيك": "#06b6d4", "معادن": "#f59e0b",
            "مواد كيميائية": "#ec4899", "نسيج": "#8b5cf6", "زجاج": "#3b82f6", "ورق": "#a3a3a3"
        }
        category_distribution = [
            CategoryChartItem(category=cat, tonnage=round(qty, 2), percentage=round(qty / total * 100, 1), color=color_map.get(cat, "#64748b"))
            for cat, qty in sorted(category_counts.items())
        ]

        # No historical trend is fabricated: this is an active snapshot, not a time series.
        monthly_trends = [TrendChartItem(month="الحالي", matches=int(potential_matches), co2_reduced_tons=round(co2_avoided, 2), traded_tons=round(reused_tons, 2))] if listings else []
        return DashboardAnalyticsResponse(kpis=kpis, category_distribution=category_distribution, monthly_trends=monthly_trends)
