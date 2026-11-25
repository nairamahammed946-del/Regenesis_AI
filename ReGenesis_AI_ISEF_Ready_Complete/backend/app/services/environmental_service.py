from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.app.models.user import Factory
from backend.app.schemas.environmental import (
    CarbonCalculationRequest, CarbonCalculationResponse,
    ProfitCalculationRequest, ProfitCalculationResponse,
    SustainabilityScoreResponse
)

# Internal illustrative placeholders only; replace with cited, region-specific factors before reporting.
# No default carbon factors are supplied; calculations require a user-provided documented factor.
CO2_BENCHMARKS = {}


class EnvironmentalService:
    @staticmethod
    def calculate_carbon(req: CarbonCalculationRequest) -> CarbonCalculationResponse:
        factor = req.emission_factor
        if factor is None:
            raise ValueError("أدخل معامل انبعاث موثقاً ومصدره وحدود النظام؛ لا توجد معاملات افتراضية معتمدة في هذه النسخة.")
        scenario_co2 = round(req.tonnage * factor, 3)

        esg_grade = "غير مصنف - لا توجد منهجية ESG معتمدة في هذا الإصدار"

        basis = f"حساب سيناريو: {req.tonnage} طن × معامل أدخله المستخدم {factor} طن CO2e/طن. يجب توثيق المصدر وحدود النظام والمادة المرجعية المستبدلة والطاقة والنقل والفواقد."
        disclaimer = "نتيجة حسابية لسيناريو فقط، وليست انبعاثات متجنبة مؤكدة أو شهادة ESG أو إثبات خفض. تتطلب المراجعة خط أساس واضحاً ومصدر معامل موثقاً وتحققاً مستقلاً."

        return CarbonCalculationResponse(
            material_type=req.material_type,
            tonnage=req.tonnage,
            co2_factor=factor,
            co2_avoided_tons=scenario_co2,
            trees_equivalent=None,
            esg_grade=esg_grade,
            calculation_basis=basis,
            disclaimer=disclaimer
        )

    @staticmethod
    def calculate_profit(req: ProfitCalculationRequest) -> ProfitCalculationResponse:
        selling_revenue = round(req.quantity_tons * req.waste_selling_price_per_ton, 2)
        virgin_cost = req.quantity_tons * req.virgin_material_price_per_ton
        buyer_savings = round(virgin_cost - selling_revenue, 2)
        processing_cost = round(req.quantity_tons * req.processing_cost_per_ton, 2)
        transport_cost = round(req.quantity_tons * req.transport_distance_km * req.transport_rate_per_ton_km, 2)
        net_benefit = round(selling_revenue + buyer_savings - processing_cost - transport_cost, 2)

        # Payback cannot be calculated without CAPEX and a defined operating period.
        roi_months = None

        assumptions = [
            f"سعر بيع مخلفات المورد (بوحدة المستخدم): {req.waste_selling_price_per_ton}/طن",
            f"سعر بديل المادة البكر (بوحدة المستخدم): {req.virgin_material_price_per_ton}/طن",
            f"تكلفة المعالجة والتجهيز (بوحدة المستخدم): {req.processing_cost_per_ton}/طن",
            f"مسافة الشحن واللوجستيات: {req.transport_distance_km} كم بتعرفة {req.transport_rate_per_ton_km}/طن/كم"
        ]

        return ProfitCalculationResponse(
            material_type=req.material_type,
            quantity_tons=req.quantity_tons,
            potential_selling_revenue=selling_revenue,
            buyer_raw_material_savings=buyer_savings,
            total_processing_cost=processing_cost,
            total_transport_cost=transport_cost,
            net_economic_benefit=net_benefit,
            roi_estimated_months=roi_months,
            assumptions_summary=assumptions,
            disclaimer="حساب توضيحي لمدخلات المستخدم وبنفس وحدة العملة المستخدمة في كل الحقول؛ لا يمثل سعراً سوقياً أو عرضاً ملزماً أو دراسة جدوى معتمدة. أدخل عروض أسعار حقيقية وتكاليف تشغيل موثقة قبل الاعتماد."
        )

    @staticmethod
    def get_or_calculate_sustainability(
        db: Session,
        factory_id: str
    ) -> SustainabilityScoreResponse:
        f_stmt = select(Factory).where(Factory.id == factory_id)
        f_res = db.execute(f_stmt)
        factory = f_res.scalars().first()
        f_name = factory.name if factory else "منشأة غير محددة"

        # No independently verified operational data is available to calculate a defensible score yet.
        w_reuse = m_exchange = w_diversion = c_impact = r_efficiency = overall = 0.0
        formula = ("لم يتم إصدار درجة استدامة رقمية: لا توجد بعد بيانات تشغيلية موثقة وكافية عن الكميات المعاد استخدامها، "
                   "التبادل الفعلي، التحويل عن المدافن، عوامل الانبعاث وحدود النظام. تُعرض الدرجة صفراً كحالة بيانات غير متاحة، لا كتقييم أداء.")

        return SustainabilityScoreResponse(
            factory_id=factory_id,
            factory_name=f_name,
            overall_score=overall,
            waste_reuse_score=w_reuse,
            material_exchange_score=m_exchange,
            waste_diversion_score=w_diversion,
            environmental_impact_score=c_impact,
            resource_efficiency_score=r_efficiency,
            badge_level="غير مقيم - بيانات غير كافية",
            evaluation_formula_explained=formula,
            last_evaluated_at=datetime.now(timezone.utc)
        )
