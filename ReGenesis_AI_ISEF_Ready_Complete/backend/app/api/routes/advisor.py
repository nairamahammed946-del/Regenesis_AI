import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.schemas.dashboard import AdvisorIn, AdvisorOut
from backend.app.services.listing_service import ListingService
from backend.app.ai.advisor import AIAdvisor
from backend.app.ai.vision_analyzer import analyze_image
from backend.app.core.config import settings
from backend.app.ai.web_search import search_web
from backend.app.api.deps import get_current_user
from backend.app.models.user import User, Factory
from backend.app.api.deps import get_current_user_optional
from backend.app.ai.knowledge_base import catalog_materials, catalog_pathways, DOCUMENTS
from backend.app.ai.climate_trace import search_industrial_assets

router = APIRouter(prefix="/advisor", tags=["REGENESIS AI Agent"])

def require_demo_or_user(user: User | None) -> None:
    if user is None and (not settings.DEMO_MODE or settings.ENVIRONMENT.lower() == "production"):
        raise HTTPException(status_code=401, detail="يرجى تسجيل الدخول للوصول إلى المساعد.")


def get_factory_context(db: Session) -> list[dict]:
    rows = db.query(Factory).order_by(Factory.is_verified.desc(), Factory.name.asc()).limit(200).all()
    return [{
        "id": f.id, "name": f.name, "sector": f.sector, "role": f.role, "city": f.city,
        "address": f.address, "description": f.description, "is_verified": f.is_verified,
        "data_origin": f.data_origin, "source_name": f.source_name,
        "source_url": f.source_url, "source_date": f.source_date,
        "contact_email": f.contact_email, "contact_phone": f.contact_phone,
    } for f in rows]


@router.get("/status")
async def advisor_status():
    """Check whether local models are downloaded and whether Ollama is currently serving them."""
    import httpx
    reachable = False
    available_models: list[str] = []
    running_models: list[str] = []
    error = None
    if settings.OLLAMA_ENABLED:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                tags = await client.get(settings.OLLAMA_BASE_URL.rstrip("/") + "/api/tags")
                tags.raise_for_status()
                reachable = True
                available_models = [m.get("name", "") for m in tags.json().get("models", [])]
                try:
                    ps = await client.get(settings.OLLAMA_BASE_URL.rstrip("/") + "/api/ps")
                    if ps.is_success:
                        running_models = [m.get("name", "") for m in ps.json().get("models", [])]
                except Exception:
                    running_models = []
        except Exception as exc:
            error = type(exc).__name__
    chat_available = settings.OLLAMA_MODEL in available_models
    vision_available = settings.OLLAMA_VISION_MODEL in available_models
    chat_running = settings.OLLAMA_MODEL in running_models
    vision_running = settings.OLLAMA_VISION_MODEL in running_models
    return {
        "ollama_enabled": settings.OLLAMA_ENABLED,
        "ollama_reachable": reachable,
        "chat_model": settings.OLLAMA_MODEL,
        "chat_model_available": chat_available,
        "chat_model_running": chat_running,
        "vision_model": settings.OLLAMA_VISION_MODEL,
        "vision_model_available": vision_available,
        "vision_model_running": vision_running,
        "knowledge_documents": len(DOCUMENTS),
        "error_type": error,
        "note": "Available means downloaded locally. Ollama loads a model into memory when an inference request is made."
    }


@router.get("/materials")
def advisor_materials(query: str = "", limit: int = 100):
    return {"count": len(catalog_materials(query, limit)), "items": catalog_materials(query, limit)}


@router.get("/pathways")
def advisor_pathways(material: str = "", limit: int = 100):
    rows = catalog_pathways(material, limit)
    return {"count": len(rows), "items": rows}

class WebSearchIn(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    max_results: int = Field(default=5, ge=1, le=8)

@router.post("/web-search")
async def advisor_web_search(payload: WebSearchIn, current_user: User = Depends(get_current_user)):
    """Search the public web through the configured provider and return traceable sources."""
    if not settings.WEB_SEARCH_ENABLED:
        raise HTTPException(status_code=503, detail="البحث على الإنترنت غير مفعّل. اضبط WEB_SEARCH_ENABLED ومفتاح مزود البحث في إعدادات الخادم.")
    try:
        results = await search_web(payload.query, payload.max_results)
    except Exception:
        raise HTTPException(status_code=502, detail="تعذر الاتصال بمزود البحث حالياً.")
    return {"query": payload.query, "count": len(results), "results": results}

@router.get("/industrial-assets")
async def public_industrial_assets(
    country_code: str = "EGY",
    sector: str = "manufacturing",
    year: int = 2025,
    limit: int = 25,
    current_user: User = Depends(get_current_user)
):
    """Query public Climate TRACE industrial emissions assets (not verified factories)."""
    if not 2021 <= year <= 2030 or not 1 <= limit <= 100:
        raise HTTPException(status_code=422, detail="year must be 2021-2030 and limit 1-100")
    try:
        return await search_industrial_assets(country_code, sector, year, limit)
    except Exception:
        raise HTTPException(status_code=502, detail="تعذر الوصول إلى واجهة Climate TRACE حالياً؛ الواجهة في إصدار تجريبي.")

@router.post("", response_model=AdvisorOut)
async def ask_advisor(query: AdvisorIn, current_user: User | None = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    require_demo_or_user(current_user)
    listings = ListingService.list_listings(db, limit=500)
    list_dicts = [ListingService.to_legacy_dict(l) for l in listings]
    result = await AIAdvisor.answer(query.message, list_dicts, query.history or [], factory_records=get_factory_context(db))
    return AdvisorOut(**result)


@router.post("/stream")
async def stream_advisor(query: AdvisorIn, current_user: User | None = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    require_demo_or_user(current_user)
    listings = ListingService.list_listings(db, limit=500)
    list_dicts = [ListingService.to_legacy_dict(l) for l in listings]
    factory_records = get_factory_context(db)
    async def token_stream():
        async for token in AIAdvisor.stream_answer(query.message, list_dicts, query.history or [], factory_records=factory_records):
            yield token
    return StreamingResponse(token_stream(), media_type="text/plain; charset=utf-8", headers={"Cache-Control":"no-cache", "X-Accel-Buffering":"no"})

@router.post("/analyze-image")
async def analyze_waste_image(file: UploadFile = File(...), note: str = Form(default=""), current_user: User | None = Depends(get_current_user_optional)):
    require_demo_or_user(current_user)
    allowed={"image/jpeg","image/png","image/webp","image/bmp"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=415, detail="ارفع صورة بصيغة JPG أو PNG أو WEBP أو BMP فقط.")
    raw=await file.read(settings.MAX_UPLOAD_SIZE+1)
    if len(raw)>settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="حجم الصورة أكبر من الحد المسموح.")
    try:
        result=await analyze_image(raw,note)
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc))
    except httpx_error_types() as exc:
        raise HTTPException(status_code=503,detail="موديل تحليل الصور غير متاح. تأكد من تشغيل Ollama وتنزيل موديل الرؤية qwen2.5vl:3b.")
    # Keep a private local copy for follow-up; filename is generated, never user supplied.
    os.makedirs(settings.UPLOAD_DIR,exist_ok=True)
    suffix={"image/jpeg":".jpg","image/png":".png","image/webp":".webp","image/bmp":".bmp"}[file.content_type]
    filename=f"waste-{uuid.uuid4().hex}{suffix}"
    with open(os.path.join(settings.UPLOAD_DIR,filename),"wb") as handle: handle.write(raw)
    result["image_url"]="/uploads/"+filename
    return result

def httpx_error_types():
    import httpx
    return (httpx.HTTPError, RuntimeError)
