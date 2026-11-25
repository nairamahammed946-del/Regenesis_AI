"""Visual triage for industrial waste.

Primary path: local Qwen2.5-VL via Ollama. If unavailable, only neutral image
metadata is returned; the fallback does not guess a material from pixel colour.
"""
from __future__ import annotations

import json
import os
import re
from typing import List, Dict, Any, Optional
from PIL import Image, ImageStat, UnidentifiedImageError

from backend.app.core.config import settings
from backend.app.ai.vision_analyzer import analyze_image


CATEGORY_ALIASES = {
    "plastic": "بلاستيك", "polymer": "بلاستيك", "pet": "بلاستيك", "hdpe": "بلاستيك", "pp": "بلاستيك",
    "metal": "معادن", "metals": "معادن", "aluminium": "معادن", "aluminum": "معادن", "steel": "معادن", "copper": "معادن",
    "wood": "خشب", "sawdust": "خشب", "textile": "نسيج", "textiles": "نسيج", "fabric": "نسيج", "cotton": "نسيج",
    "glass": "زجاج", "paper": "ورق", "cardboard": "ورق", "rubber": "مطاط", "organic": "عضوي",
    "electronic": "إلكترونيات", "e-waste": "إلكترونيات", "chemical": "مواد كيميائية",
}


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _parse_model_json(raw: str) -> dict:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.S)
        if not match:
            return {}
        try:
            value = json.loads(match.group(0))
            return value if isinstance(value, dict) else {}
        except json.JSONDecodeError:
            return {}


class WasteScanner:
    @classmethod
    def analyze_image_features(cls, file_path: str) -> Dict[str, Any]:
        """Extract neutral file/colour metadata; do not infer material identity from colour."""
        try:
            if not os.path.exists(file_path):
                return {"valid": False, "error": "File not found"}
            with Image.open(file_path) as img:
                image = img.convert("RGB")
                width, height = image.size
                stat = ImageStat.Stat(image)
                means = tuple(round(x, 1) for x in stat.mean)
                spreads = tuple(round(x, 1) for x in stat.stddev)
                return {
                    "valid": True,
                    "width": width,
                    "height": height,
                    "mean_rgb": means,
                    "rgb_stddev": spreads,
                    "filename": os.path.basename(file_path),
                }
        except (UnidentifiedImageError, OSError) as exc:
            return {"valid": False, "error": str(exc)}

    @classmethod
    async def analyze(
        cls,
        image_paths: List[str],
        video_path: Optional[str] = None,
        user_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not image_paths:
            raise ValueError("يرجى إرفاق صورة واحدة على الأقل.")

        # Validate and extract neutral metadata for every supplied image.
        features = [cls.analyze_image_features(path) for path in image_paths]
        valid_features = [item for item in features if item.get("valid")]
        if not valid_features:
            raise ValueError("لم يتم العثور على صورة صالحة للتحليل.")

        vision_data: dict = {}
        vision_text = ""
        model_error = ""
        if settings.OLLAMA_ENABLED:
            try:
                with open(image_paths[0], "rb") as handle:
                    result = await analyze_image(handle.read(), user_notes or "")
                vision_text = str(result.get("analysis", ""))
                vision_data = _parse_model_json(vision_text)
            except Exception as exc:
                model_error = type(exc).__name__

        if vision_data:
            raw_category = str(vision_data.get("likely_category", "غير محسوم بصرياً")).strip()
            category = CATEGORY_ALIASES.get(raw_category.lower(), raw_category or "غير محسوم بصرياً")[:100]
            material = (str(vision_data.get("likely_material", "غير محسوم بصرياً")).strip() or "غير محسوم بصرياً")[:150]
            visual = _as_list(vision_data.get("visible_features"))
            if user_notes:
                visual.append("ملاحظة المستخدم: " + user_notes[:500])
            contamination = str(vision_data.get("visible_contamination", "لا يمكن تأكيد الملوثات غير الظاهرة من الصورة وحدها.")).strip()
            condition = str(vision_data.get("condition", "غير محسومة بصرياً")).strip()[:100]
            routes = _as_list(vision_data.get("possible_reuse_routes"))
            questions = _as_list(vision_data.get("questions_for_user"))
            safety = _as_list(vision_data.get("safety_notes"))
            try:
                confidence = float(vision_data.get("confidence", 0.0))
                if confidence > 1.0:
                    confidence = confidence / 100.0
            except (TypeError, ValueError):
                confidence = 0.0
            confidence = max(0.0, min(1.0, confidence))
            return {
                "predicted_category": category,
                "predicted_material_type": material,
                "visual_characteristics": visual or ["لم يقدم موديل الرؤية تفاصيل مرئية منظمة."],
                "color": "يُراجع الوصف المرئي أعلاه؛ لا يُستنتج التركيب من اللون.",
                "shape": "يُراجع الوصف المرئي أعلاه.",
                "approximate_size": "لا يمكن تقدير المقاس بدقة دون مرجع قياس في الصورة.",
                "visible_contamination": contamination + " غياب الملوثات بصرياً لا يثبت خلو العينة منها.",
                "material_condition": condition,
                "potential_applications": routes,
                "possible_recycling_methods": routes,
                "suggested_reuse_opportunities": routes,
                "confidence_score": confidence,
                "testing_recommendations": questions + safety + [
                    "تأكيد هوية الخامة والتركيب/نوع البوليمر بعينة ممثلة واختبار مناسب.",
                    "قياس الرطوبة والملوثات والخواص المطلوبة حسب مواصفة المشتري.",
                ],
                "analysis_mode": "ollama-qwen2.5vl-visual-triage",
                "lab_verification_status": "غير متحقق معملياً — يحتاج عينة واختبارات",
                "disclaimer": "تحليل بصري بواسطة نموذج Qwen Vision فقط؛ لا يثبت التركيب الكيميائي أو درجة البوليمر أو النقاء أو السلامة أو المطابقة الصناعية. لا تعتمد أي قرار شراء أو معالجة قبل أخذ عينة ممثلة وإجراء الاختبارات اللازمة.",
                "image_paths": image_paths,
                "video_path": video_path,
                "model": settings.OLLAMA_VISION_MODEL,
            }

        if vision_text:
            first = valid_features[0]
            return {
                "predicted_category": "غير محسوم — راجع وصف النموذج",
                "predicted_material_type": "أعاد نموذج Qwen Vision وصفاً نصياً دون JSON منظم.",
                "visual_characteristics": [vision_text[:4000]],
                "color": "راجع الوصف النصي؛ لا يُستنتج التركيب من اللون.",
                "shape": "راجع الوصف النصي.",
                "approximate_size": "لا يمكن تقدير المقاس بدقة دون مرجع قياس.",
                "visible_contamination": "لا يمكن تأكيد الملوثات غير الظاهرة من الصورة وحدها.",
                "material_condition": "غير محسومة بصرياً.",
                "potential_applications": [],
                "possible_recycling_methods": [],
                "suggested_reuse_opportunities": [],
                "confidence_score": 0.0,
                "testing_recommendations": ["أعد التحليل مع صورة أوضح أو اطلب إخراجاً منظماً من النموذج.", "أكد نوع الخام والملوثات والخواص المطلوبة باختبارات معملية."],
                "analysis_mode": "ollama-qwen2.5vl-unstructured-response",
                "lab_verification_status": "غير متحقق معملياً",
                "disclaimer": "النموذج المحلي قدّم وصفاً نصياً فقط ولم يتم استخراج حقول موثوقة؛ لا تستخدمه لتأكيد هوية الخامة أو جودتها. يلزم فحص معمل.",
                "image_paths": image_paths,
                "video_path": video_path,
                "model": settings.OLLAMA_VISION_MODEL,
            }

        # Clearly identified fallback: no material prediction is made without the vision model.
        first = valid_features[0]
        notes = [f"عدد الصور الصالحة: {len(valid_features)}.", f"دقة الصورة الأولى: {first['width']}×{first['height']} بكسل.", "تم استخراج بيانات الصورة الأساسية فقط؛ لم يتم التعرف على نوع الخامة لأن موديل الرؤية لم يرجع تحليلاً منظماً."]
        if user_notes:
            notes.append("ملاحظة المستخدم: " + user_notes[:500])
        if model_error:
            notes.append("حالة اتصال نموذج الرؤية: " + model_error)
        if video_path:
            notes.append("تم حفظ ملف الفيديو؛ لم يتم تحليل إطارات الفيديو في هذا المسار.")
        return {
            "predicted_category": "غير محسوم بصرياً",
            "predicted_material_type": "يلزم تحديد الخامة من وصف المستخدم أو فحصها؛ لا يمكن الجزم من الألوان وحدها.",
            "visual_characteristics": notes,
            "color": "معلومات RGB تقنية فقط؛ لا تستخدم لتحديد المادة.",
            "shape": "غير محدد — يحتاج مراجعة بصرية.",
            "approximate_size": "غير محدد — لا يوجد مرجع قياس.",
            "visible_contamination": "لم يتم تقييم الملوثات؛ الصورة لا تثبت خلو المادة من التلوث.",
            "material_condition": "غير محسومة.",
            "potential_applications": [],
            "possible_recycling_methods": [],
            "suggested_reuse_opportunities": [],
            "confidence_score": 0.0,
            "testing_recommendations": [
                "شغّل Ollama وتأكد من تنزيل نموذج الرؤية qwen2.5vl:3b لإجراء التحليل البصري المحلي.",
                "حدد مصدر الخامة واستخدم اختبار تعريف مناسب (مثل FTIR للبوليمرات أو XRF/OES للمعادن حسب الحالة).",
                "افحص الرطوبة والملوثات والخصائص المطلوبة وفق مواصفة المشتري.",
            ],
            "analysis_mode": "image-metadata-fallback-no-vision-model",
            "lab_verification_status": "لم يتم التعرف على المادة — لم يبدأ التحقق المعملي",
            "disclaimer": "لم يعمل نموذج الرؤية في هذا التحليل؛ لم نصدر أي تنبؤ بنوع المادة. البيانات المكانية واللونية ليست تحليلاً للخامة. شغّل qwen2.5vl:3b ثم أعد المحاولة، واعتمد دائماً على الاختبارات المعملية.",
            "image_paths": image_paths,
            "video_path": video_path,
        }
