"""Offline-first ReGenesis knowledge retrieval grounded in packaged CSV references."""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "datasets"

BASE_DOCUMENTS = [
    {"title": "PET recycling routes", "text": "PET (polyethylene terephthalate) is commonly sorted by polymer type and color, cleaned, shredded, washed, dried and processed into flakes or pellets. Potential outlets include fiber, strapping and non-food packaging, subject to contamination, color, intrinsic viscosity and buyer specifications. Food-contact use requires applicable regulatory controls and validated decontamination."},
    {"title": "HDPE recycling routes", "text": "HDPE waste can be sorted, washed, dried, shredded and melt-filtered before extrusion or pelletizing. Potential applications include non-pressure pipes, crates, pallets and containers when grade, additives and contamination are suitable. Do not assume recycled resin is suitable for pressure or food-contact applications without testing and standards compliance."},
    {"title": "Wood residues", "text": "Clean untreated sawdust and wood offcuts may be considered for particleboard, fiberboard, pellets or briquettes. Painted, glued, preservative-treated or chemically contaminated wood requires separate assessment and may be unsuitable for fuel or material recovery."},
    {"title": "Aluminium scrap", "text": "Aluminium scrap value depends strongly on alloy family, separation, coatings, oils, moisture and oxidation. Sort by alloy where possible, remove non-metal attachments and assess contamination before remelting. Mixed alloy scrap can downgrade product properties."},
    {"title": "Industrial waste safety", "text": "Visual inspection cannot confirm polymer grade, chemical composition, hazardous contamination, moisture, mechanical properties or regulatory classification. Use representative sampling and laboratory testing before processing, transport, sale or reuse. Treat unknown chemical containers, powders, batteries and e-waste as potentially hazardous and use qualified handlers."},
    {"title": "Circular economy matching", "text": "A potential marketplace match requires more than matching category: compare material specification, quantity, location, delivery frequency, purity, processing capability, buyer acceptance criteria, price and applicable permits. Platform matches are leads, not verified commercial or technical approvals."},
    {"title": "Carbon accounting", "text": "Avoided-emissions estimates depend on the chosen methodology, geography, energy mix, transport, processing losses and displaced virgin material. Never present a generic factor as a verified carbon credit or audited ESG result. Show assumptions and uncertainty."},
]


def _csv_rows(filename: str) -> list[dict]:
    path = DATA_DIR / filename
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _build_documents() -> list[dict]:
    docs = list(BASE_DOCUMENTS)
    for row in _csv_rows("scrap_material_catalog.csv"):
        title = f"كتالوج خامة: {row.get('material_name_ar', '')} / {row.get('material_name_en', '')}"
        fields = [
            ("الفئة", row.get("category")),
            ("مصدر المخلفات المعتاد", row.get("typical_source")),
            ("ملاحظات قابلية التدوير", row.get("recyclability_notes")),
            ("فحوص الجودة", row.get("key_quality_checks")),
            ("مسار التدوير المعتاد", row.get("common_recycling_route")),
            ("مسارات الرفع من القيمة", row.get("potential_upcycling_routes")),
            ("السلامة والاشتراطات", row.get("safety_or_regulatory_note")),
            ("حالة البيانات", row.get("data_status")),
        ]
        text = "\n".join(f"{label}: {value}" for label, value in fields if value)
        docs.append({"title": title, "text": text, "source": "scrap_material_catalog.csv"})
    for row in _csv_rows("recycling_upcycling_pathways.csv"):
        title = f"مسار تدوير وUpcycling: {row.get('input_material', '')}"
        fields = [
            ("المتطلبات قبل المعالجة", row.get("preconditions")),
            ("خطوات المعالجة", row.get("process_route")),
            ("الناتج المحتمل", row.get("potential_output")),
            ("القطاعات المستخدمة", row.get("potential_user_industries")),
            ("الاختبارات المهمة", row.get("critical_tests")),
            ("الحدود والمخاطر", row.get("limitations")),
            ("أساس المرجع", row.get("reference_basis")),
            ("درجة الثقة الوصفية", row.get("confidence_label")),
        ]
        text = "\n".join(f"{label}: {value}" for label, value in fields if value)
        docs.append({"title": title, "text": text, "source": "recycling_upcycling_pathways.csv"})
    return docs


DOCUMENTS = _build_documents()

SYNONYMS = {
    "خشب": {"wood", "sawdust", "timber"},
    "نشارة": {"sawdust", "wood"},
    "بلاستيك": {"plastic", "polymer", "pet", "hdpe"},
    "معادن": {"metal", "metals", "aluminium", "aluminum", "steel", "copper"},
    "ألومنيوم": {"aluminium", "aluminum"},
    "الومنيوم": {"aluminium", "aluminum"},
    "قطن": {"cotton", "fabric"},
    "قماش": {"fabric", "cotton"},
    "معدن": {"metal", "metals"},
    "زجاج": {"glass", "cullet"},
    "نسيج": {"textile", "textiles", "cotton", "fabric"},
    "منسوجات": {"textile", "textiles", "fabric"},
    "ورق": {"paper", "cardboard"},
    "كرتون": {"cardboard", "paper"},
    "مطاط": {"rubber", "tire"},
    "إلكترونيات": {"electronics", "electronic", "e-waste"},
    "كابلات": {"cable", "copper"},
    "خردة": {"scrap", "waste", "recovery"},
    "مخلفات": {"waste", "byproduct", "scrap"},
    "تدوير": {"recycling", "recycle"},
    "اعادة": {"recycling", "reuse"},
    "تدويرها": {"recycling", "recycle"},
    "رفع": {"upcycling", "value"},
    "القيمة": {"upcycling", "value"},
    "معالجة": {"process", "processing", "route"},
    "نقاء": {"purity", "quality"},
    "سعر": {"price", "cost"},
    "مشتري": {"buyer", "demand"},
    "مشترين": {"buyer", "demand"},
    "مورد": {"supplier", "supply"},
    "مصنع": {"factory", "plant"},
}


def _terms(value: str) -> set[str]:
    text = str(value).lower()
    text = text.translate(str.maketrans({"أ":"ا", "إ":"ا", "آ":"ا", "ٱ":"ا", "ى":"ي", "ؤ":"و", "ئ":"ي"}))
    text = re.sub(r"[\u064b-\u065f\u0670]", "", text)
    raw = re.findall(r"[a-z0-9]+|[\u0621-\u064a]+", text)
    stop_words = {"ما", "ماذا", "كيف", "هل", "هو", "هي", "من", "في", "على", "عن", "الى", "الي", "مع", "هذا", "هذه", "ذلك", "التي", "الذي", "و", "عايز", "عاوزه", "اريد", "أريد", "ممكن", "ازاي", "ازاى", "ايه", "اعمل", "أعمل", "استخدام", "the", "and", "for", "from", "with", "into", "to", "of", "a", "an", "what", "can", "i", "do", "how", "used", "we", "you", "me"}
    terms: set[str] = set()
    for word in raw:
        if len(word) < 2 or word in stop_words:
            continue
        terms.add(word)
        variants = [word]
        for prefix in ("بال", "وال", "لل", "ال", "ل", "و", "ف", "ب", "ك"):
            if word.startswith(prefix) and len(word) > len(prefix) + 1:
                variants.append(word[len(prefix):])
        for variant in variants:
            if len(variant) < 2:
                continue
            terms.add(variant)
            terms.update(SYNONYMS.get(variant, set()))
    return terms


def retrieve(query: str, limit: int = 6) -> List[dict]:
    """Simple deterministic lexical retrieval across bundled materials and pathways."""
    terms = _terms(query)
    if not terms:
        return [doc for doc in DOCUMENTS if doc.get("source") == "recycling_upcycling_pathways.csv"][:max(1, limit)]
    generic_terms = {"upcycling", "upcycle", "recycling", "recycle", "waste", "scrap", "material", "materials", "route", "routes", "pathway", "pathways", "مسار", "مسارات", "طرق", "طريقة", "تدوير", "مخلفات", "خردة", "إعادة", "رفع", "قيمة", "value"}
    specific_terms = {term for term in terms if term not in generic_terms and len(term) > 2}
    scored = []
    for doc in DOCUMENTS:
        hay = _terms(doc.get("title", "") + " " + doc.get("text", ""))
        overlap = terms.intersection(hay)
        specific_overlap = specific_terms.intersection(hay)
        # When a particular material was named, do not pad the result with unrelated routes.
        if specific_terms and not specific_overlap:
            continue
        score = len(overlap) + (3 * len(specific_overlap))
        title_terms = _terms(doc.get("title", ""))
        score += 2 * len(terms.intersection(title_terms))
        if score:
            scored.append((score, doc))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [doc for _, doc in scored[:limit]]


def catalog_materials(query: str = "", limit: int = 100) -> list[dict]:
    rows = _csv_rows("scrap_material_catalog.csv")
    if query:
        terms = _terms(query)
        rows = [row for row in rows if terms.intersection(_terms(" ".join(str(v) for v in row.values())))]
    return rows[:max(1, min(int(limit), 250))]


def catalog_pathways(material: str = "", limit: int = 100) -> list[dict]:
    rows = _csv_rows("recycling_upcycling_pathways.csv")
    if material:
        terms = _terms(material)
        rows = [row for row in rows if terms.intersection(_terms(" ".join(str(v) for v in row.values())))]
    return rows[:max(1, min(int(limit), 250))]
