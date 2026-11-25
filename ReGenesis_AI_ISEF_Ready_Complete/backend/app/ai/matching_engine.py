from typing import Dict, Any, Tuple, List
import math

class SmartMatchingEngine:
    """
    AI Smart Matching Engine:
    Calculates multi-factor explainable compatibility between waste supply and buyer demand.
    Considers material classification, trade complementarity, quantity, purity, location, and price alignment.
    Never uses random numbers; produces deterministic, explainable mathematical scores.
    """

    @classmethod
    def score_listings(cls, supply: Dict[str, Any], demand: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        # 1. Category Matching (Weight: 35%)
        supply_cat = str(supply.get("category", "")).strip().lower()
        demand_cat = str(demand.get("category", "")).strip().lower()
        
        # Check matching or sub-matching
        cat_match = 0.0
        if supply_cat == demand_cat:
            cat_match = 1.0
        elif any(k in supply_cat and k in demand_cat for k in ["خشب", "بلاستيك", "معادن", "كيميائ", "نسيج", "زجاج"]):
            cat_match = 0.95
        else:
            cat_match = 0.0

        # 2. Trade Type Complementarity (Weight: 20%)
        # Needs Supply (عرض) meets Demand (طلب)
        st = str(supply.get("trade_type") or supply.get("tradeType") or "").lower()
        dt = str(demand.get("trade_type") or demand.get("tradeType") or "").lower()
        
        is_complementary = (
            ("عرض" in st and "طلب" in dt) or
            ("طلب" in st and "عرض" in dt) or
            ("supply" in st and "demand" in dt) or
            ("demand" in st and "supply" in dt)
        )
        trade_score = 1.0 if is_complementary else 0.1

        # 3. Quantity Compatibility (Weight: 15%)
        sq = float(supply.get("quantity") or supply.get("qty") or 1.0)
        dq = float(demand.get("quantity") or demand.get("qty") or 1.0)
        
        q_min = min(sq, dq)
        q_max = max(sq, dq, 1.0)
        # Quantity fulfillment ratio
        quantity_score = round(min(1.0, q_min / q_max), 3)

        # 4. Purity & Quality Alignment (Weight: 12%)
        sp = float(supply.get("purity") or 90.0)
        dp = float(demand.get("purity") or 90.0)
        
        # If supplier purity meets or exceeds buyer requirement: full score
        if sp >= dp:
            purity_score = 1.0
        else:
            purity_score = max(0.0, 1.0 - (dp - sp) / 100.0)
        purity_score = round(purity_score, 3)

        # 5. Geographic Proximity / Logistics (Weight: 8%)
        sc = str(supply.get("city") or "").strip().lower()
        dc = str(demand.get("city") or "").strip().lower()
        
        if sc == dc or (sc and dc and sc in dc) or (sc and dc and dc in sc):
            location_score = 1.0
            dist_desc = "نفس المدينة والمنطقة الصناعية (تكلفة نقل منخفضة جداً)"
        elif any(c in sc and c in dc for c in ["دمياط", "أكتوبر", "رمضان", "السادات", "حلوان", "القاهرة", "الإسكندرية"]):
            location_score = 0.85
            dist_desc = "منطقة صناعية متقاربة لوجستياً"
        else:
            location_score = 0.60
            dist_desc = "مسافة نقل متوسطة بين المحافظات"

        # 6. Price Alignment (Weight: 10%)
        s_price = float(supply.get("price") or 0.0)
        d_price = float(demand.get("price") or 0.0)
        
        if s_price > 0 and d_price > 0:
            price_gap = abs(s_price - d_price) / max(s_price, d_price, 1.0)
            price_score = max(0.0, round(1.0 - price_gap, 3))
        else:
            price_score = 0.85  # Neutral if one party hasn't specified price

        # Overall Weighted Score Calculation
        overall = (
            cat_match * 0.35 +
            trade_score * 0.20 +
            quantity_score * 0.15 +
            purity_score * 0.12 +
            location_score * 0.08 +
            price_score * 0.10
        ) * 100.0

        final_score = round(overall, 1)

        # Build Explainable Reasoning
        reasons = []
        if cat_match >= 0.95:
            reasons.append(f"تطابق تام في التصنيف الصناعي ({supply.get('category')})")
        if is_complementary:
            reasons.append("تكامل تعاقدي: عرض خامات يقابل طلباً استهلاكياً مباشراً")
        if quantity_score >= 0.6:
            reasons.append(f"توافق كمي بنسبة {int(quantity_score * 100)}% (تغطية {q_min} طن من أصل {q_max} طن)")
        if purity_score >= 0.9:
            reasons.append(f"درجة النقاء المسجلة ({sp}%) تلبي متطلبات الجودة المطلوبة ({dp}%)")
        reasons.append(f"الاعتبار اللوجستي: {dist_desc}")

        # Missing information analysis
        missing_info = []
        if not supply.get("lab_verified"):
            missing_info.append("شهادة الفحص المعملي الكيميائي للدفعة غير مرفقة حتى الآن")
        if s_price == 0:
            missing_info.append("السعر النهائي للطن يخضع للتفاوض المباشر")

        # Suggested Next Steps
        suggested_steps = [
            "إرسال طلب استفسار أو تفاوض مبدئي عبر منصة ReGenesis",
            "طلب عينة معملية مرجعية تزن 5 كجم للتأكد من مواصفات المصهور والرطوبة",
            "الاتفاق على شروط النقل والتفريغ في مستودعات المشتري",
            "توثيق بيانات الصفقة الفعلية وفحص المادة قبل احتساب أي أثر بيئي"
        ]

        breakdown = {
            "category_score": round(cat_match * 100, 1),
            "trade_score": round(trade_score * 100, 1),
            "quantity_score": round(quantity_score * 100, 1),
            "purity_score": round(purity_score * 100, 1),
            "location_score": round(location_score * 100, 1),
            "price_score": round(price_score * 100, 1)
        }

        explanation = f"درجة توافق أولية {final_score}% (ليست موافقة فنية أو عقداً): " + "؛ ".join(reasons[:3])

        return final_score, {
            "score": final_score,
            "explanation": explanation,
            "breakdown": breakdown,
            "reasons": reasons,
            "missing_info": missing_info,
            "suggested_steps": suggested_steps
        }
