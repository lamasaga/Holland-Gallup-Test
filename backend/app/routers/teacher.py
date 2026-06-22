from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app import models, schemas, auth
from app.database import get_db

router = APIRouter(prefix="/api/teacher", tags=["teacher"])


@router.get("/students", response_model=List[schemas.StudentListItem])
def list_students(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_teacher)
):
    students = db.query(models.User).filter(models.User.role == models.UserRole.student).all()
    result = []
    for s in students:
        assessment = db.query(models.AssessmentStatus).filter(
            models.AssessmentStatus.user_id == s.id
        ).first()
        result.append({
            "id": s.id,
            "username": s.username,
            "display_name": s.display_name,
            "holland_done": bool(assessment.holland_done) if assessment else False,
            "gallup_done": bool(assessment.gallup_done) if assessment else False,
            "holland_code": assessment.holland_code if assessment else None,
            "gallup_domain": assessment.gallup_domain if assessment else None,
            "gallup_secondary_domain": assessment.gallup_secondary_domain if assessment else None,
        })
    return result
