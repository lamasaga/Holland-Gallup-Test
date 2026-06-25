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
    admin = "admin"


class UserBase(BaseModel):
    username: str
    display_name: Optional[str] = None
    role: UserRole


class UserCreate(BaseModel):
    username: str
    password: Optional[str] = None
    display_name: Optional[str] = None
    email: Optional[str] = None
    grade: Optional[str] = None
    class_name: Optional[str] = None
    school: Optional[str] = None
    phone: Optional[str] = None


class StudentRegister(BaseModel):
    username: str
    password: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    grade: Optional[str] = None
    class_name: Optional[str] = None
    school: Optional[str] = None
    phone: Optional[str] = None


class AdminUserCreate(UserCreate):
    role: UserRole = UserRole.student


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    grade: Optional[str] = None
    class_name: Optional[str] = None
    school: Optional[str] = None
    phone: Optional[str] = None
    career_note: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    grade: Optional[str] = None
    class_name: Optional[str] = None
    school: Optional[str] = None
    phone: Optional[str] = None
    career_note: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ResetPasswordRequest(BaseModel):
    new_password: Optional[str] = None


class ResetPasswordResponse(BaseModel):
    username: str
    new_password: str
    must_change_password: bool = True


class UserOut(UserBase):
    id: str
    email: Optional[str] = None
    grade: Optional[str] = None
    class_name: Optional[str] = None
    school: Optional[str] = None
    phone: Optional[str] = None
    career_note: Optional[str] = None
    profile_complete: bool = False
    must_change_password: bool = False
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: str
    username: str
    display_name: Optional[str] = None
    profile_complete: bool = False
    must_change_password: bool = False


class LoginRequest(BaseModel):
    username: str
    password: str


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
    dual_side_covered: Optional[int] = None
    a_side_ratio: float
    b_side_ratio: float
    dual_side_ratio: Optional[float] = None
    themes_scored: Optional[int] = None


class HollandQuality(BaseModel):
    differentiation: int
    is_flat: bool
    response_quality: Optional[Dict[str, Any]] = None


class ResponseQuality(BaseModel):
    score: float
    flags: List[str]
    risk_level: str
    message_zh: str
    message_en: str
    details: Optional[Dict[str, Any]] = None


class GallupQuality(BaseModel):
    response_quality: Optional[ResponseQuality] = None


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
    gallup_quality: Optional[GallupQuality] = None


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
    email: Optional[str] = None
    grade: Optional[str] = None
    class_name: Optional[str] = None
    school: Optional[str] = None
    phone: Optional[str] = None
    profile_complete: bool = False
    is_active: bool = True
    holland_done: bool
    gallup_done: bool
    holland_code: Optional[str]
    gallup_domain: Optional[str]
    gallup_secondary_domain: Optional[str] = None


class PlatformStats(BaseModel):
    total_users: int
    students: int
    teachers: int
    admins: int
    completed_assessments: int
    holland_completed: int
    gallup_completed: int


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
    gallup_quality: Optional[GallupQuality] = None


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
    gallup_quality: Optional[GallupQuality] = None
