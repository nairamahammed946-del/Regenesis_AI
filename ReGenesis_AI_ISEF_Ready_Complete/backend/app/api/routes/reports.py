from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Enterprise Audit & ESG Reports"])

@router.get("/factory/{factory_id}")
def get_factory_audit_report(factory_id: str, db: Session = Depends(get_db)):
    """Generate comprehensive factory sustainability and circular economy audit report."""
    return ReportService.generate_factory_report(db, factory_id)
