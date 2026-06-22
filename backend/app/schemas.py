from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class QuestionOut(BaseModel):
    id: str
    assessment_type: str
    question_num: int
    statement_a: Optional[str] = None
    statement_b: Optional[str] = None
    scenario_hint: Optional[str] = None
    theme_tags: List[str]
    b_side_themes: Optional[List[str]] = None

    class Config:
        from_attributes = True


class UserRole(str, Enum):
    student = "student"
    teacher = "teacher"


class UserBase(BaseModel):
    username: str
    display_name: Optional[str] = None
    role: UserRole


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: str
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str
    role: UserRole


class HollandAnswerItem(BaseModel):
    question_num: int
    score: int = Field(..., ge=1, le=5)


class HollandSubmit(BaseModel):
    answers: List[HollandAnswerItem]


class GallupAnswerItem(BaseModel):
    question_num: int
    choice: int = Field(..., ge=-2, le=2)  # -2=very B, -1=somewhat B, 0=neutral, 1=somewhat A, 2=very A


class GallupSubmit(BaseModel):
    answers: List[GallupAnswerItem]


class GallupCoverage(BaseModel):
    total_questions: int
    a_side_covered: int
    b_side_covered: int
    a_side_ratio: float
    b_side_ratio: float


class HollandQuality(BaseModel):
    differentiation: int
    is_flat: bool


class AssessmentProgress(BaseModel):
    holland_done: bool
    gallup_done: bool
    holland_code: Optional[str] = None
    gallup_top5: Optional[List[str]] = None
    gallup_domain: Optional[str] = None
    gallup_secondary_domain: Optional[str] = None
    holland_scores: Optional[Dict[str, int]] = None
    gallup_coverage: Optional[GallupCoverage] = None
    holland_quality: Optional[HollandQuality] = None


class AssessmentOut(BaseModel):
    id: str
    user_id: str
    holland_done: bool
    gallup_done: bool
    holland_scores: Dict[str, int]
    holland_code: Optional[str]
    gallup_top5: List[str]
    gallup_top10: List[str]
    gallup_domain: Optional[str]
    status: Dict[str, Any]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class StudentListItem(BaseModel):
    id: str
    username: str
    display_name: Optional[str]
    holland_done: bool
    gallup_done: bool
    holland_code: Optional[str]
    gallup_domain: Optional[str]
    gallup_secondary_domain: Optional[str] = None


class ReportStudent(BaseModel):
    student_name: str
    holland_code: str
    holland_scores: Dict[str, int]
    gallup_top5: List[str]
    gallup_domain: str
    careers: List[Dict[str, Any]]
    actions: List[str]
    report_html: str
    data_quality_notes: List[str] = []
    gallup_coverage: Optional[GallupCoverage] = None
    holland_quality: Optional[HollandQuality] = None


class ReportProfessional(BaseModel):
    student_name: str
    holland_scores: Dict[str, int]
    holland_code: str
    gallup_top5: List[Dict[str, Any]]
    gallup_top10: List[str]
    gallup_domain: str
    gallup_secondary_domain: Optional[str] = None
    domain_distribution: Dict[str, int]
    tension: str
    careers: List[Dict[str, Any]]
    evidence_note: str
    report_html: str
    data_quality_notes: List[str] = []
    gallup_coverage: Optional[GallupCoverage] = None
    holland_quality: Optional[HollandQuality] = None
