from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app import models, schemas, auth
from app.database import get_db
from app.services.holland import calculate_holland
from app.services.gallup import calculate_gallup
from app.services.response_quality import evaluate_holland_quality, evaluate_gallup_quality

router = APIRouter(prefix="/api/assessments", tags=["assessments"])


@router.get("/questions", response_model=List[schemas.QuestionOut])
def get_questions(
    assessment_type: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    questions = db.query(models.Question).filter(
        models.Question.assessment_type == assessment_type
    ).order_by(models.Question.question_num).all()
    return questions


@router.get("/progress", response_model=schemas.AssessmentProgress)
def get_progress(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    assessment = auth.get_or_create_assessment(db, current_user.id)
    status = assessment.status or {}
    return {
        "holland_done": bool(assessment.holland_done),
        "gallup_done": bool(assessment.gallup_done),
        "holland_code": assessment.holland_code,
        "gallup_top5": assessment.gallup_top5,
        "gallup_domain": assessment.gallup_domain,
        "gallup_secondary_domain": assessment.gallup_secondary_domain,
        "holland_scores": assessment.holland_scores,
        "gallup_coverage": status.get("gallup_coverage"),
        "holland_quality": status.get("holland_quality"),
        "gallup_quality": status.get("gallup_quality"),
    }


def _validate_holland_answers(answers: List[schemas.HollandAnswerItem], db: Session):
    """Validate Holland answer count and question number range."""
    if len(answers) != 60:
        raise HTTPException(
            status_code=400,
            detail=f"Holland 测评需要提交 60 道题目，当前收到 {len(answers)} 道。"
        )
    expected_nums = set(range(1, 61))
    received_nums = {a.question_num for a in answers}
    missing = expected_nums - received_nums
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Holland 测评缺少题号：{sorted(missing)}。"
        )
    extra = received_nums - expected_nums
    if extra:
        raise HTTPException(
            status_code=400,
            detail=f"Holland 测评包含非法题号：{sorted(extra)}。"
        )


def _validate_gallup_answers(answers: List[schemas.GallupAnswerItem], db: Session):
    """Validate Gallup answer count and question number range."""
    if len(answers) != 180:
        raise HTTPException(
            status_code=400,
            detail=f"Gallup 测评需要提交 180 道题目，当前收到 {len(answers)} 道。"
        )
    expected_nums = set(range(1, 181))
    received_nums = {a.question_num for a in answers}
    missing = expected_nums - received_nums
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Gallup 测评缺少题号：{sorted(missing)[:10]}{'...' if len(missing) > 10 else ''}。"
        )
    extra = received_nums - expected_nums
    if extra:
        raise HTTPException(
            status_code=400,
            detail=f"Gallup 测评包含非法题号：{sorted(extra)}。"
        )


@router.post("/holland", response_model=schemas.AssessmentProgress)
def submit_holland(
    data: schemas.HollandSubmit,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    _validate_holland_answers(data.answers, db)

    # Build question map from DB for robust scoring
    questions = db.query(models.Question).filter(
        models.Question.assessment_type == "holland"
    ).all()
    question_map = {q.question_num: (q.theme_tags or []) for q in questions}

    result = calculate_holland([a.model_dump() for a in data.answers], question_map)
    assessment = auth.get_or_create_assessment(db, current_user.id)
    assessment.holland_scores = result["scores"]
    assessment.holland_code = result["code"]
    assessment.holland_done = 1

    status = dict(assessment.status or {})
    holland_response_quality = evaluate_holland_quality([a.model_dump() for a in data.answers])
    status["holland_quality"] = {
        "differentiation": result["differentiation"],
        "is_flat": result["is_flat"],
        "response_quality": holland_response_quality,
    }
    status["holland_used_fallback"] = result["used_fallback"]
    assessment.status = status

    if assessment.gallup_done:
        assessment.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(assessment)
    return {
        "holland_done": bool(assessment.holland_done),
        "gallup_done": bool(assessment.gallup_done),
        "holland_code": assessment.holland_code,
        "gallup_top5": assessment.gallup_top5,
        "gallup_domain": assessment.gallup_domain,
        "gallup_secondary_domain": assessment.gallup_secondary_domain,
        "holland_scores": assessment.holland_scores,
        "gallup_coverage": status.get("gallup_coverage"),
        "holland_quality": status.get("holland_quality"),
    }


@router.post("/gallup", response_model=schemas.AssessmentProgress)
def submit_gallup(
    data: schemas.GallupSubmit,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    _validate_gallup_answers(data.answers, db)

    # Build per-question A-side and B-side theme maps from DB
    questions = db.query(models.Question).filter(
        models.Question.assessment_type == "gallup"
    ).all()
    a_map = {}
    b_map = {}
    for q in questions:
        a_map[q.question_num] = q.theme_tags or []
        b_map[q.question_num] = q.b_side_themes or []

    result = calculate_gallup([a.model_dump() for a in data.answers], a_map, b_map)
    assessment = auth.get_or_create_assessment(db, current_user.id)
    assessment.gallup_scores = result["scores"]
    assessment.gallup_top5 = result["top5"]
    assessment.gallup_top10 = result["top10"]
    assessment.gallup_domain = result["domain"]
    assessment.gallup_secondary_domain = result["secondary_domain"]
    assessment.gallup_done = 1

    status = dict(assessment.status or {})
    gallup_response_quality = evaluate_gallup_quality([a.model_dump() for a in data.answers])
    status["gallup_coverage"] = result["coverage"]
    status["gallup_quality"] = {"response_quality": gallup_response_quality}
    assessment.status = status

    if assessment.holland_done:
        assessment.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(assessment)
    return {
        "holland_done": bool(assessment.holland_done),
        "gallup_done": bool(assessment.gallup_done),
        "holland_code": assessment.holland_code,
        "gallup_top5": assessment.gallup_top5,
        "gallup_domain": assessment.gallup_domain,
        "gallup_secondary_domain": assessment.gallup_secondary_domain,
        "holland_scores": assessment.holland_scores,
        "gallup_coverage": status.get("gallup_coverage"),
        "holland_quality": status.get("holland_quality"),
        "gallup_quality": status.get("gallup_quality"),
    }
