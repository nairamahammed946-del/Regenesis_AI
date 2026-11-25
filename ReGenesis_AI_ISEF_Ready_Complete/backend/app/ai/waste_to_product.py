from typing import List, Dict, Any
from backend.app.ai.knowledge_base import catalog_pathways


class WasteToProductEngine:
    """Maps candidate waste-to-product pathways to the local technical catalog; no invented ROI."""

    @classmethod
    def get_products(cls, category: str) -> List[Dict[str, Any]]:
        rows = catalog_pathways(category, limit=100)
        products = []
        for row in rows:
            products.append({
                "product_name": row.get("potential_output", "منتج محتمل غير محدد"),
                "target_industry": row.get("potential_user_industries", "غير محدد"),
                "transformation_process": row.get("process_route", "يلزم توصيف العملية"),
                "processing_requirements": row.get("preconditions", "يلزم تقييم أولي للعينة"),
                "critical_tests": row.get("critical_tests", ""),
                "limitations": row.get("limitations", ""),
                "estimated_value_per_ton": None,
                "value_addition_multiplier": "غير محسوب — يتطلب عروض أسعار فعلية لخام الإدخال والمنتج النهائي.",
                "economic_viability": "غير محددة دون CAPEX وOPEX وأسعار طاقة ونقل وعروض شراء موثقة.",
                "payback_period": "لا يمكن حسابها دون دراسة جدوى وبيانات تشغيل محلية.",
                "assumptions": row.get("reference_basis", "مسار مرجعي عام") + "؛ مستوى الثقة: " + str(row.get("confidence_label", "غير محدد")),
                "validation_notice": "مسار محتمل فقط؛ تحقق من خصائص المادة والاشتراطات والمعايير الصناعية قبل التنفيذ.",
            })
        return products
