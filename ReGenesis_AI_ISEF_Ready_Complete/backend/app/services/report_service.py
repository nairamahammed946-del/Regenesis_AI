import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.app.models.user import Factory
from backend.app.models.waste import WasteListing

class ReportService:
    @staticmethod
    def generate_factory_report(db: Session, factory_id: str) -> Dict[str, Any]:
        f_stmt = select(Factory).where(Factory.id == factory_id)
        f_res = db.execute(f_stmt)
        factory = f_res.scalars().first()
        f_name = factory.name if factory else "مصنع صناعي مسجل"
        f_city = factory.city if factory else "المنطقة الصناعية"

        l_stmt = select(WasteListing).where(WasteListing.factory_id == factory_id)
        l_res = db.execute(l_stmt)
        listings = list(l_res.scalars().all())

        total_registered_qty = sum(float(l.quantity) for l in listings)
        active_listings_count = len(listings)

        # No carbon factor or transaction ledger is attached to these listing rows.
        co2_avoided = None
        economic_value = None  # Listing currency and completed transaction ledger are not yet modelled.

        return {
            "report_id": f"REG-REP-2026-{uuid.uuid4().hex[:6].upper()}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "factory_profile": {
                "id": factory_id,
                "name": f_name,
                "city": f_city,
                "sector": factory.sector if factory else "صناعات عامة",
                "role": factory.role if factory else "Waste Producer & Recycler",
                "sustainability_score": factory.sustainability_score if factory else 0.0
            },
            "operational_metrics": {
                "registered_waste_materials_count": active_listings_count,
                "total_registered_tonnage": total_registered_qty,
                "diverted_from_landfills_tons": None,
                "successful_circular_exchanges": 0
            },
            "environmental_esg_impact": {
                "co2_emissions_avoided_tons": co2_avoided,
                "equivalent_trees_planted": None,
                "energy_conserved_mwh": None,
                "audit_certificate_status": "Not certified - verified operational data and emission factors required"
            },
            "economic_benefits": {
                "estimated_financial_value_generated_usd": economic_value,
                "raw_material_purchasing_savings_usd": None,
                "landfill_disposal_fees_avoided_usd": None
            },
            "compliance_statement": (
                "تقرير تجميعي أولي لسجلات المنصة، وليس تقرير تدقيق أو شهادة امتثال. "
                "القيم الاقتصادية مستنتجة من أسعار وكميات الإعلانات المدخلة، ولا تثبت إتمام صفقة أو تحصيل قيمة."
            )
        }
