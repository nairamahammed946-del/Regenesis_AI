from typing import List, Dict, Any
from backend.app.ai.knowledge_base import catalog_pathways


class ReuseRecommender:
    """Retrieves source-attributed pathway guidance from the packaged 18-row CSV catalog."""

    @classmethod
    def get_recommendations(cls, category: str, purity: float = 90.0) -> List[Dict[str, Any]]:
        rows = catalog_pathways(category, limit=100)
        results = []
        for row in rows:
            results.append({
                "pathway_name": row.get("input_material", "مسار تدوير/استخدام"),
                "suitable_sectors": [x.strip() for x in str(row.get("potential_user_industries", "")).split(";") if x.strip()],
                "manufactured_products": [row.get("potential_output", "")],
                "processing_methods": [row.get("process_route", "")],
                "technical_requirements": [row.get("preconditions", "")],
                "limitations": row.get("limitations", ""),
                "critical_tests": row.get("critical_tests", ""),
                "confidence_label": row.get("confidence_label", "غير محدد"),
                "reference_basis": row.get("reference_basis", "قاعدة المسارات المحلية"),
                "lab_validation_required": True,
                "purity_input_percent": float(purity),
                "validation_notice": "النتيجة استرجاع لمسار مرجعي عام؛ لا تعني أن النقاء المدخل تم التحقق منه أو أن العملية مناسبة دون فحوص ومعايير المصنع.",
            })
        return results
