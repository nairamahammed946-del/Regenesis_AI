import base64
import io
from typing import Any, Dict
import httpx
from PIL import Image, UnidentifiedImageError
from backend.app.core.config import settings

VISION_PROMPT = (
 "You are ReGenesis industrial waste visual triage assistant. Inspect only visible evidence. "
 "Return ONLY valid JSON, without markdown fences or extra prose, with: likely_category, likely_material, visible_features, "
 "visible_contamination, condition, possible_reuse_routes, confidence (0-1), "
 "questions_for_user, safety_notes. If uncertain say unknown. Never claim chemical/polymer grade, "
 "purity, hazardous status, or lab certification from an image. Answer in Arabic if the user writes Arabic."
)

async def analyze_image(image_bytes: bytes, user_note: str = "") -> Dict[str, Any]:
    try:
        image=Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except (UnidentifiedImageError, OSError):
        raise ValueError("الملف ليس صورة صالحة.")
    if image.width < 80 or image.height < 80:
        raise ValueError("الصورة صغيرة جداً؛ ارفع صورة أوضح.")
    image.thumbnail((1280,1280))
    buf=io.BytesIO(); image.save(buf, format="JPEG", quality=88, optimize=True)
    encoded=base64.b64encode(buf.getvalue()).decode("ascii")
    prompt=VISION_PROMPT + ("\nUser context: "+user_note[:1000] if user_note else "")
    payload={"model":settings.OLLAMA_VISION_MODEL,"messages":[{"role":"user","content":prompt,"images":[encoded]}],"stream":False,"options":{"temperature":0.1}}
    async with httpx.AsyncClient(timeout=httpx.Timeout(settings.OLLAMA_TIMEOUT_SECONDS)) as client:
        response=await client.post(settings.OLLAMA_BASE_URL.rstrip("/")+"/api/chat",json=payload)
        response.raise_for_status()
        data=response.json()
    answer=str(data.get("message",{}).get("content","")).strip()
    if not answer: raise RuntimeError("لم يرجع موديل الرؤية نتيجة.")
    return {"analysis":answer,"model":settings.OLLAMA_VISION_MODEL,"mode":"ollama-local-vision","disclaimer":"تحليل بصري أولي فقط؛ لا يثبت التركيب الكيميائي أو درجة النقاء أو السلامة. يلزم أخذ عينة واختبارها قبل اتخاذ قرار صناعي."}
