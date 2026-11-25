from typing import Dict, Any, List, Optional


CATEGORY_TERMS = {
    "خشب": ["خشب", "نشارة", "wood", "sawdust"],
    "بلاستيك": ["بلاستيك", "pet", "hdpe", "pp", "plastic", "polymer"],
    "معادن": ["معادن", "معدن", "ألومنيوم", "نحاس", "حديد", "metal", "aluminium", "copper", "steel"],
    "نسيج": ["نسيج", "قطن", "قماش", "textile", "cotton", "polyester"],
    "زجاج": ["زجاج", "glass", "cullet"],
    "ورق": ["ورق", "كرتون", "paper", "cardboard"],
    "مطاط": ["مطاط", "إطارات", "rubber", "tire"],
}


class SmartNegotiationAssistant:
    """Negotiation guidance grounded in current listing comparisons, never invented market benchmarks."""

    @classmethod
    def analyze_price(
        cls,
        material_type: str,
        quantity: float,
        purity: float,
        current_asking_price: float,
        city: str,
        market_listings: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        category = None
        material_lower = material_type.lower()
        for key, words in CATEGORY_TERMS.items():
            if any(word in material_lower for word in words):
                category = key
                break
        if category is None:
            category = material_type

        comparables = []
        for row in market_listings or []:
            trade = str(row.get("trade_type") or row.get("tradeType") or "")
            if "عرض" not in trade and "offer" not in trade.lower() and "supply" not in trade.lower():
                continue
            row_category = str(row.get("category", ""))
            title = str(row.get("title", ""))
            if category.lower() not in row_category.lower() and not any(word in (row_category + " " + title).lower() for word in CATEGORY_TERMS.get(category, [])):
                continue
            price = float(row.get("price") or 0)
            if price <= 0:
                continue
            comparables.append(row)

        prices = [float(row.get("price") or 0) for row in comparables]
        min_price = round(min(prices), 2) if prices else None
        max_price = round(max(prices), 2) if prices else None
        all_demo = bool(comparables) and all(row.get("data_origin") == "demo_synthetic" for row in comparables)
        if not comparables:
            data_status = "no_comparable_listings"
            label = "لا توجد إعلانات مقارنة لهذه الفئة حالياً. لا يمكن اقتراح نطاق سعر موثوق."
        elif all_demo:
            data_status = "synthetic_showcase_only"
            label = "النطاق المستخرج من سجلات العرض التجريبية فقط؛ ليس نطاق سعر سوق أو توصية تفاوض حقيقية."
        else:
            data_status = "unverified_user_listings"
            label = "النطاق محسوب من أسعار إعلانات منصة غير متحققة؛ لا يمثل متوسط سوق موثقاً."

        tips = [
            "اطلب صورة حديثة للدفعة الفعلية وعينة ممثلة قبل الاتفاق.",
            "حدد نوع المادة والدرجة/السبيكة ونسبة الشوائب والرطوبة وطريقة القياس في المواصفة.",
            "اتفق كتابةً على الكمية الصافية، التعبئة، التحميل، النقل، ومكان التسليم.",
            "اربط السعر النهائي بنتيجة الفحص ومعيار قبول المشتري وشروط الرفض أو الخصم.",
        ]
        return {
            "material_type": material_type,
            "category_matched": category,
            "quantity_tons": quantity,
            "purity_entered_percent": purity,
            "current_asking_price": current_asking_price,
            "currency": "EGP",
            "comparables_count": len(comparables),
            "submitted_listing_price_min": min_price,
            "submitted_listing_price_max": max_price,
            "recommended_min_price": None,
            "recommended_max_price": None,
            "fair_market_price": None,
            "historical_platform_average": None,
            "data_status": data_status,
            "basis_of_estimate": [label, "لم يتم استخدام أسعار تاريخية أو معاملات سوق خارجية."],
            "negotiation_tips": tips,
            "disclaimer": "لا تقدم هذه الأداة سعراً عادلاً أو متوسط سوق. أسعار السوق في وضع العرض افتراضية، وأسعار الإعلانات الحقيقية التي يدخلها المستخدمون غير متحققة تلقائياً. استند إلى عروض فعلية متزامنة وعينة فنية وفواتير/عقود موثقة قبل التفاوض.",
        }
