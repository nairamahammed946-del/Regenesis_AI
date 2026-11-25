import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.config import settings
from backend.app.schemas.waste import MaterialAnalysisResult
from backend.app.models.waste import MaterialAnalysis
from backend.app.ai.waste_scanner import WasteScanner
from backend.app.ai.reuse_recommender import ReuseRecommender
from backend.app.ai.waste_to_product import WasteToProductEngine
from backend.app.api.deps import get_current_user_optional
from backend.app.models.user import User

router = APIRouter(prefix="/analysis", tags=["AI Waste Scanner & Material Intelligence"])

@router.post("/scan", response_model=MaterialAnalysisResult)
async def scan_waste(
    images: List[UploadFile] = File(...),
    video: Optional[UploadFile] = File(None),
    user_notes: Optional[str] = Form(None),
    factory_name: Optional[str] = Form(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """
    AI Waste Scanner: Analyze single or multiple images and short videos of industrial waste.
    Generates a structured 12-point material intelligence report distinguishing
    visual observations from laboratory-validated results.
    """
    if current_user is None and (not settings.DEMO_MODE or settings.ENVIRONMENT.lower() == "production"):
        raise HTTPException(status_code=401, detail="يرجى تسجيل الدخول لإجراء تحليل صورة.")
    saved_image_paths = []
    if not images and video is None:
        raise HTTPException(status_code=400, detail="يرجى إرفاق صورة واحدة على الأقل أو فيديو")
    for img in images:
        if img.content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"نوع الصورة ({img.content_type}) غير مدعوم. الصيغ المدعومة: JPEG, PNG, WebP"
            )
        file_ext = os.path.splitext(img.filename or "image.jpg")[1].lower() or ".jpg"
        if file_ext not in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
            raise HTTPException(status_code=400, detail="امتداد الصورة غير مدعوم")
        unique_name = f"scan_{uuid.uuid4().hex[:10]}{file_ext}"
        target_path = os.path.join(settings.UPLOAD_DIR, unique_name)
        
        content = await img.read(settings.MAX_UPLOAD_SIZE + 1)
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=400, detail="حجم الملف يتجاوز الحد الأقصى (50 ميجابايت)")
        
        with open(target_path, "wb") as f:
            f.write(content)
        saved_image_paths.append(target_path)

    saved_video_path = None
    if video:
        if video.content_type not in settings.ALLOWED_VIDEO_TYPES:
            raise HTTPException(status_code=400, detail="نوع الفيديو غير مدعوم")
        v_ext = os.path.splitext(video.filename or "video.mp4")[1].lower() or ".mp4"
        if v_ext not in {".mp4", ".webm", ".mov", ".avi"}:
            raise HTTPException(status_code=400, detail="امتداد الفيديو غير مدعوم")
        v_name = f"video_{uuid.uuid4().hex[:10]}{v_ext}"
        saved_video_path = os.path.join(settings.UPLOAD_DIR, v_name)
        v_content = await video.read(settings.MAX_UPLOAD_SIZE + 1)
        if len(v_content) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=400, detail="حجم الفيديو يتجاوز الحد الأقصى")
        with open(saved_video_path, "wb") as f:
            f.write(v_content)

    # Perform visual intelligence analysis
    analysis = await WasteScanner.analyze(
        image_paths=saved_image_paths,
        video_path=saved_video_path,
        user_notes=user_notes
    )

    # Persist analysis report in DB
    report_record = MaterialAnalysis(
        predicted_category=analysis["predicted_category"],
        predicted_material_type=analysis["predicted_material_type"],
        visual_characteristics=analysis["visual_characteristics"],
        color=analysis["color"],
        shape=analysis["shape"],
        approximate_size=analysis["approximate_size"],
        visible_contamination=analysis["visible_contamination"],
        material_condition=analysis["material_condition"],
        potential_applications=analysis["potential_applications"],
        possible_recycling_methods=analysis["possible_recycling_methods"],
        suggested_reuse_opportunities=analysis["suggested_reuse_opportunities"],
        confidence_score=analysis["confidence_score"],
        testing_recommendations=analysis["testing_recommendations"],
        analysis_mode=analysis["analysis_mode"],
        image_paths=[os.path.basename(p) for p in saved_image_paths],
        video_path=os.path.basename(saved_video_path) if saved_video_path else None
    )
    db.add(report_record)
    db.flush()

    analysis["id"] = report_record.id
    analysis["image_paths"] = [f"/uploads/{os.path.basename(p)}" for p in saved_image_paths]
    analysis["created_at"] = report_record.created_at

    return MaterialAnalysisResult.model_validate(analysis)

@router.get("/recommendations/{category}")
async def get_reuse_recommendations(category: str, purity: float = 90.0):
    """Retrieve verified circular economy reuse pathways and technical requirements."""
    return ReuseRecommender.get_recommendations(category, purity)

@router.get("/waste-to-product/{category}")
async def get_waste_to_product(category: str):
    """Explore high-value product transformation opportunities and economic feasibility."""
    return WasteToProductEngine.get_products(category)
