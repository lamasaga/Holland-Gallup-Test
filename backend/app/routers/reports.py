from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas, auth
from app.database import get_db
from app.services.report import generate_student_report, generate_professional_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _require_student_exists(db: Session, student_id: str):
    """Verify the referenced user exists and is a student; raise 404 otherwise."""
    user = db.query(models.User).filter(models.User.id == student_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Student not found")
    if user.role != models.UserRole.student:
        raise HTTPException(status_code=400, detail="Requested user is not a student")
    return user


@router.get("/student", response_model=schemas.ReportStudent)
def student_report(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    assessment = auth.get_or_create_assessment(db, current_user.id)
    if not (assessment.holland_done and assessment.gallup_done):
        raise HTTPException(status_code=400, detail="Please complete both assessments first")
    return generate_student_report(db, current_user.id)


@router.get("/professional/{student_id}", response_model=schemas.ReportProfessional)
def professional_report(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_teacher)
):
    _require_student_exists(db, student_id)
    assessment = auth.get_or_create_assessment(db, student_id)
    if not (assessment.holland_done and assessment.gallup_done):
        raise HTTPException(status_code=400, detail="Student has not completed both assessments")
    return generate_professional_report(db, student_id)


@router.get("/student/{student_id}", response_model=schemas.ReportStudent)
def teacher_view_student_report(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_teacher)
):
    _require_student_exists(db, student_id)
    assessment = auth.get_or_create_assessment(db, student_id)
    if not (assessment.holland_done and assessment.gallup_done):
        raise HTTPException(status_code=400, detail="Student has not completed both assessments")
    return generate_student_report(db, student_id)
