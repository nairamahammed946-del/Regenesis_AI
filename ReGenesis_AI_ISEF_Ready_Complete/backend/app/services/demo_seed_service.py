"""Idempotent ISEF showcase data loader.

Public directory records are imported with source attribution and remain unverified.
Marketplace offers/requests are synthetic scenarios with illustrative generated images
and illustrative EGP values. They are not live seller quotes or real company accounts.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.user import Factory
from backend.app.models.waste import WasteCategory, WasteListing
from backend.app.models.matching import MatchEvent
from backend.app.ai.matching_engine import SmartMatchingEngine

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "datasets"

CATEGORY_META = {
    "خشب": ("Wood & Cellulose", "نشارة وبقايا تشغيل أخشاب نظيفة.", 0.0, "fa-tree"),
    "بلاستيك": ("Plastics & Polymers", "مخلفات بوليمرات PET وHDPE وPP مفروزة.", 0.0, "fa-bottle-water"),
    "معادن": ("Industrial Metals", "خردة ألومنيوم ونحاس وحديد؛ يلزم تحديد السبيكة والتلوث.", 0.0, "fa-gears"),
    "مواد كيميائية": ("Industrial Chemicals", "مواد تتطلب توصيفاً وتصنيفاً واختبارات سلامة متخصصة.", 0.0, "fa-flask"),
    "نسيج": ("Textiles & Fibers", "قصاصات أقمشة وألياف صناعية أو طبيعية.", 0.0, "fa-shirt"),
    "زجاج": ("Glass & Ceramics", "كسر زجاج مفروز حسب اللون وخالٍ قدر الإمكان من السيراميك.", 0.0, "fa-wine-glass"),
    "ورق": ("Paper & Cardboard", "ورق وكرتون مفروز وجاف.", 0.0, "fa-box"),
    "مخلفات معدنية/إنشائية": ("Mineral & Construction Residues", "مخلفات صناعية معدنية/إنشائية يلزم تقييمها حسب الاستخدام.", 0.0, "fa-industry"),
    "مخلفات صناعية": ("Industrial Residues", "مخلفات صناعية متنوعة تتطلب توصيفاً فنياً قبل إعادة الاستخدام.", 0.0, "fa-industry"),
    "عضوي": ("Organic By-products", "مخلفات عضوية قابلة للتقييم للتسميد أو الاسترجاع الحيوي.", 0.0, "fa-leaf"),
    "مطاط": ("Rubber & Tires", "مطاط وإطارات مستهلكة؛ يلزم فصل المكونات والتحقق من الملوثات.", 0.0, "fa-circle"),
    "إلكترونيات": ("Electrical & Electronic Waste", "مخلفات إلكترونية تُدار بواسطة جهات مؤهلة ومصرح لها.", 0.0, "fa-microchip"),
}

CITIES = [
    "العاشر من رمضان", "السادس من أكتوبر", "مدينة السادات", "برج العرب", "القاهرة",
    "الجيزة", "دمياط", "الإسكندرية", "بدر", "العبور", "بني سويف", "قنا"
]

# Every profile below is deliberately synthetic and visibly named as a showcase record.
DEMO_FACTORY_SPECS = [
    ("01", "مورد مخلفات البلاستيك", "بلاستيك", "Waste Producer", "العاشر من رمضان"),
    ("02", "مورد مخلفات البلاستيك", "بلاستيك", "Waste Producer", "السادس من أكتوبر"),
    ("03", "مورد مخلفات البلاستيك", "بلاستيك", "Waste Producer", "مدينة السادات"),
    ("04", "مورد خردة المعادن", "معادن", "Waste Producer", "برج العرب"),
    ("05", "مورد خردة المعادن", "معادن", "Waste Producer", "العاشر من رمضان"),
    ("06", "مورد نشارة ومخلفات الخشب", "خشب", "Waste Producer", "دمياط"),
    ("07", "مورد قصاصات المنسوجات", "نسيج", "Waste Producer", "المحلة الكبرى"),
    ("08", "مورد كسر الزجاج", "زجاج", "Waste Producer", "القاهرة"),
    ("09", "مورد مخلفات البلاستيك", "بلاستيك", "Waste Producer", "بدر"),
    ("10", "مورد مخلفات البلاستيك", "بلاستيك", "Waste Producer", "الإسكندرية"),
    ("11", "مورد خردة المعادن", "معادن", "Waste Producer", "حلوان"),
    ("12", "مورد قصاصات المنسوجات", "نسيج", "Waste Producer", "مدينة السادات"),
    ("13", "مشتري بوليمرات معاد تدويرها", "بلاستيك", "Raw Material Buyer", "العاشر من رمضان"),
    ("14", "مشتري بوليمرات معاد تدويرها", "بلاستيك", "Raw Material Buyer", "السادس من أكتوبر"),
    ("15", "مشتري خامات معدنية", "معادن", "Raw Material Buyer", "برج العرب"),
    ("16", "مشتري خامات معدنية", "معادن", "Raw Material Buyer", "القاهرة"),
    ("17", "مشتري نشارة ومخلفات خشب", "خشب", "Raw Material Buyer", "دمياط"),
    ("18", "مشتري ألياف ومنسوجات", "نسيج", "Raw Material Buyer", "المحلة الكبرى"),
    ("19", "مشتري كسر زجاج", "زجاج", "Raw Material Buyer", "الإسكندرية"),
    ("20", "مشتري بوليمرات معاد تدويرها", "بلاستيك", "Raw Material Buyer", "مدينة السادات"),
    ("21", "مشتري خامات معدنية", "معادن", "Raw Material Buyer", "العاشر من رمضان"),
    ("22", "مشتري خامات خشبية", "خشب", "Raw Material Buyer", "السادس من أكتوبر"),
    ("23", "مشتري ألياف ومنسوجات", "نسيج", "Raw Material Buyer", "بدر"),
    ("24", "مشتري زجاج معاد تدويره", "زجاج", "Raw Material Buyer", "القاهرة"),
]

MATERIALS = [
    {"key":"PET", "title":"رقائق بلاستيك PET شفافة مغسولة", "category":"بلاستيك", "image":"pet_flakes.jpg", "qty":(6, 28), "purity":(88, 98), "price":(13000, 20500), "description":"رقائق PET ناتجة عن عبوات مفروزة. السيناريو يفترض غسيلاً أولياً؛ يجب اختبار الرطوبة واللون والتلوث وPVC واللزوجة الذاتية حسب الاستخدام."},
    {"key":"HDPE", "title":"مجروش بلاستيك HDPE مفروز", "category":"بلاستيك", "image":"polymer_pellets.jpg", "qty":(5, 25), "purity":(86, 97), "price":(14500, 23000), "description":"مجروش HDPE افتراضي مفروز حسب اللون. يلزم التحقق من الراتنج وبقايا العبوات ومعدل تدفق المصهور والكثافة قبل البثق."},
    {"key":"PP", "title":"قصاصات ومجروش بولي بروبيلين PP", "category":"بلاستيك", "image":"polymer_pellets.jpg", "qty":(4, 20), "purity":(85, 96), "price":(13500, 21500), "description":"قصاصات إنتاج PP افتراضية. يلزم فصل البوليمر وإزالة المعادن والغبار وقياس MFI قبل إعادة التحبيب أو الحقن."},
    {"key":"AL", "title":"خراطة وخردة ألومنيوم صناعي", "category":"معادن", "image":"aluminum_scrap.jpg", "qty":(2, 16), "purity":(90, 99), "price":(72000, 112000), "description":"خراطة ألومنيوم توضيحية. السعر لا يحدد السبيكة؛ يلزم فصل الدرجات واختبار OES وفحص الزيوت والرطوبة والشوائب قبل الصهر."},
    {"key":"WOOD", "title":"نشارة وبقايا خشب طبيعي جافة", "category":"خشب", "image":"wood_sawdust.jpg", "qty":(8, 40), "purity":(82, 97), "price":(1200, 2600), "description":"نشارة وأجزاء خشب نظيفة افتراضياً. يلزم قياس الرطوبة واستبعاد الخشب المعالج أو المطلي أو الملوث قبل الألواح أو القوالب."},
    {"key":"COTTON", "title":"قصاصات أقمشة قطنية مفروزة", "category":"نسيج", "image":"textile_scraps.jpg", "qty":(3, 18), "purity":(80, 96), "price":(6500, 13500), "description":"قصاصات قطنية جافة افتراضية مفروزة حسب اللون. يلزم تحديد نسب الخلط بالألياف والأصباغ والرطوبة قبل التفكيك أو إعادة الغزل."},
    {"key":"POLY", "title":"قصاصات أقمشة بوليستر صناعي", "category":"نسيج", "image":"textile_scraps.jpg", "qty":(3, 16), "purity":(82, 96), "price":(6000, 12500), "description":"قصاصات بوليستر صناعي افتراضية. يلزم تحديد نسبة PET والخلطات والطلاءات قبل إعادة التدوير الميكانيكي أو استخدامها كألياف حشو."},
    {"key":"GLASS", "title":"كسر زجاج شفاف مفروز Cullet", "category":"زجاج", "image":"glass_cullet.jpg", "qty":(5, 30), "purity":(88, 98), "price":(900, 1900), "description":"كسر زجاج توضيحي مفروز حسب اللون. يلزم فحص السيراميك والحصى والمعادن والمواد العضوية وتوزيع حجم الحبيبات."},
]


def _read_csv(path: Path) -> List[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def seed_showcase_data(db: Session, enable_marketplace_demo: bool = True) -> Dict[str, int]:
    """Import source-attributed facilities and deterministic simulated B2B scenarios."""
    counts = {"categories": 0, "public_facilities": 0, "demo_factories": 0, "demo_listings": 0, "demo_matches": 0}

    # Complete categories from the local material catalogue.
    for name, (name_en, description, co2_factor, icon) in CATEGORY_META.items():
        exists = db.execute(select(WasteCategory).where(WasteCategory.name == name)).scalars().first()
        if not exists:
            db.add(WasteCategory(name=name, name_en=name_en, description=description, co2_factor=0.0, icon=icon))
            counts["categories"] += 1
        else:
            # No carbon factor is treated as validated until a documented methodology is supplied.
            exists.co2_factor = 0.0
    db.flush()

    # Import the source-attributed public recycling directory; never mark entries verified.
    for row in _read_csv(DATA_DIR / "egypt_recycling_facilities.csv"):
        name = (row.get("name") or "").strip()
        if not name:
            continue
        existing = db.execute(select(Factory).where(Factory.name == name)).scalars().first()
        if existing:
            # Upgrade only records originally imported by this seed if source metadata was absent.
            if existing.data_origin in (None, "user_submitted") and not existing.owner_id:
                existing.data_origin = "public_directory"
                existing.source_name = row.get("source_name") or None
                existing.source_url = row.get("source_url") or None
                existing.source_date = row.get("source_date") or None
                existing.is_verified = False
            continue
        desc = (row.get("description") or "").strip()
        db.add(Factory(
            name=name,
            sector=(row.get("sector") or "غير محدد").strip(),
            role=(row.get("role") or "Recycler").strip(),
            city=(row.get("city") or "غير محدد").strip(),
            address=(row.get("address") or None),
            latitude=float(row["latitude"]) if row.get("latitude") else None,
            longitude=float(row["longitude"]) if row.get("longitude") else None,
            contact_email=(row.get("contact_email") or None),
            contact_phone=(row.get("contact_phone") or None),
            description=desc + "\nبيانات دليل عام؛ يجب الاتصال بالمنشأة والتحقق من الوضع الحالي ونطاق الترخيص قبل التعاقد.",
            is_verified=False,
            data_origin="public_directory",
            source_name=(row.get("source_name") or None),
            source_url=(row.get("source_url") or None),
            source_date=(row.get("source_date") or None),
        ))
        counts["public_facilities"] += 1

    if not enable_marketplace_demo:
        db.flush()
        return counts

    demo_factories: Dict[str, Factory] = {}
    for code, role_label, sector, role, city in DEMO_FACTORY_SPECS:
        name = f"مصنع تجريبي {code} – {role_label}"
        factory = db.execute(select(Factory).where(Factory.name == name)).scalars().first()
        if not factory:
            factory = Factory(
                name=name, sector=sector, role=role, city=city,
                address="عنوان افتراضي لأغراض العرض فقط",
                description="ملف منشأة اصطناعي لأغراض تجربة REGENESIS AI وشرح تدفق السوق. لا يمثل شركة حقيقية ولا يحتوي على وسيلة اتصال أو عرض تجاري فعلي.",
                is_verified=False,
                data_origin="demo_synthetic",
                sustainability_score=0.0,
            )
            db.add(factory)
            db.flush()
            counts["demo_factories"] += 1
        demo_factories[code] = factory

    seller_by_category = {
        "بلاستيك": ["01", "02", "03", "09", "10"],
        "معادن": ["04", "05", "11"],
        "خشب": ["06"],
        "نسيج": ["07", "12"],
        "زجاج": ["08"],
    }
    buyer_by_category = {
        "بلاستيك": ["13", "14", "20"],
        "معادن": ["15", "16", "21"],
        "خشب": ["17", "22"],
        "نسيج": ["18", "23"],
        "زجاج": ["19", "24"],
    }
    serial = 1
    for material_index, material in enumerate(MATERIALS):
        seller_codes = seller_by_category[material["category"]]
        buyer_codes = buyer_by_category[material["category"]]
        img_url = f"/uploads/demo_materials/{material['image']}"
        low_qty, high_qty = material["qty"]
        low_purity, high_purity = material["purity"]
        low_price, high_price = material["price"]
        # Five offer listings and three buyer demand listings per material = 64 demo records.
        for j in range(5):
            code = seller_codes[(material_index * 2 + j) % len(seller_codes)]
            factory = demo_factories[code]
            qty = round(low_qty + ((high_qty - low_qty) * ((j + 1) / 6)), 1)
            purity = round(low_purity + ((high_purity - low_purity) * ((j + 1) / 6)), 1)
            price = round(low_price + ((high_price - low_price) * ((j + 1) / 6)), 0)
            db.add(WasteListing(
                legacy_code=f"DEMO-S-{serial:03d}",
                title=f"{material['title']} – دفعة عرض {j + 1}",
                category=material["category"], trade_type="عرض (توفر مخلفات)",
                quantity=qty, unit="طن", purity=purity, price=price, currency="EGP",
                factory_id=factory.id, factory_name=factory.name, city=factory.city,
                description=(material["description"] + "\n\nبيانات سيناريو افتراضي للعرض فقط؛ ليست مخزوناً متاحاً ولا عرض سعر من مصنع حقيقي."),
                images=[img_url], images_are_illustrative=True,
                data_origin="demo_synthetic", price_basis="سعر توضيحي افتراضي بالجنيه/طن؛ ليس سعر سوق أو عرض بيع حقيقي",
                status="Active", lab_verified=False,
                ai_match_hint="توافق أولي تجريبي؛ يحتاج تحققاً فنياً وتجارياً.",
            ))
            serial += 1
        for j in range(3):
            code = buyer_codes[(material_index * 2 + j) % len(buyer_codes)]
            factory = demo_factories[code]
            qty = round(low_qty + ((high_qty - low_qty) * ((j + 1) / 4)), 1)
            purity = round(low_purity + ((high_purity - low_purity) * ((j + 1) / 4)), 1)
            price = round(low_price + ((high_price - low_price) * ((j + 1) / 4)), 0)
            db.add(WasteListing(
                legacy_code=f"DEMO-D-{serial:03d}",
                title=f"طلب شراء {material['title']} – طلب {j + 1}",
                category=material["category"], trade_type="طلب (احتياج خامة)",
                quantity=qty, unit="طن", purity=purity, price=price, currency="EGP",
                factory_id=factory.id, factory_name=factory.name, city=factory.city,
                description=("سيناريو طلب شراء افتراضي لتوضيح آلية الربط بين المورد والمشتري. " + material["description"] + "\nليس طلب شراء حقيقياً."),
                images=[img_url], images_are_illustrative=True,
                data_origin="demo_synthetic", price_basis="سعر استرشادي افتراضي للعرض؛ ليس عرض شراء حقيقياً",
                status="Active", lab_verified=False,
                ai_match_hint="طلب تجريبي؛ يلزم تأكيد المواصفة والكمية والسعر.",
            ))
            serial += 1
    db.flush()
    counts["demo_listings"] = serial - 1

    # Create a small, explainable set of category-level candidate links for the dashboard.
    all_demo = db.execute(select(WasteListing).where(WasteListing.data_origin == "demo_synthetic")).scalars().all()
    if all_demo:
        existing_pairs = {
            (x.listing_id, x.candidate_id)
            for x in db.execute(select(MatchEvent)).scalars().all()
        }
        offers = [x for x in all_demo if "عرض" in x.trade_type]
        demands = [x for x in all_demo if "طلب" in x.trade_type]
        candidates = []
        for offer in offers:
            for demand in demands:
                if offer.category != demand.category:
                    continue
                a = {"category":offer.category,"trade_type":offer.trade_type,"quantity":offer.quantity,"purity":offer.purity,"city":offer.city,"price":offer.price}
                b = {"category":demand.category,"trade_type":demand.trade_type,"quantity":demand.quantity,"purity":demand.purity,"city":demand.city,"price":demand.price}
                score, details = SmartMatchingEngine.score_listings(a, b)
                candidates.append((score, offer, demand, details))
        candidates.sort(key=lambda item: item[0], reverse=True)
        for score, offer, demand, details in candidates[:40]:
            pair = (offer.id, demand.id)
            if pair in existing_pairs:
                continue
            breakdown = details.get("breakdown", {})
            db.add(MatchEvent(
                listing_id=offer.id, candidate_id=demand.id, score=score,
                explanation="فرصة مطابقة تجريبية بين سيناريو عرض وسيناريو طلب؛ ليست صفقة أو قبولاً فنياً.",
                category_score=breakdown.get("category_score", 0),
                trade_score=breakdown.get("trade_score", 0),
                quantity_score=breakdown.get("quantity_score", 0),
                purity_score=breakdown.get("purity_score", 0),
                location_score=breakdown.get("location_score", 0),
                price_score=breakdown.get("price_score", 0),
                reasons=details.get("reasons", []),
                missing_info=details.get("missing_info", []),
                suggested_steps=details.get("suggested_steps", []),
                status="Demo",
            ))
            counts["demo_matches"] += 1
    db.flush()
    return counts
