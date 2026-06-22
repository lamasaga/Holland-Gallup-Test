import uuid
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Enum, Integer, Float, Text
from sqlalchemy.sql import func
from app.database import Base
import enum


class UserRole(str, enum.Enum):
    student = "student"
    teacher = "teacher"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=True)
    role = Column(Enum(UserRole), nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AssessmentStatus(Base):
    __tablename__ = "assessments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Holland
    holland_done = Column(Integer, default=0)  # 0 or 1
    holland_scores = Column(JSON, default=dict)  # {R: score, I: score, ...}
    holland_code = Column(String, nullable=True)
    
    # Gallup
    gallup_done = Column(Integer, default=0)
    gallup_top5 = Column(JSON, default=list)
    gallup_top10 = Column(JSON, default=list)
    gallup_domain = Column(String, nullable=True)
    gallup_secondary_domain = Column(String, nullable=True)
    gallup_scores = Column(JSON, default=dict)  # all 34 theme scores
    
    status = Column(JSON, default=dict)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class Question(Base):
    __tablename__ = "questions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_type = Column(String, nullable=False, index=True)  # holland / gallup
    question_num = Column(Integer, nullable=False, index=True)
    statement_a = Column(Text, nullable=True)
    statement_b = Column(Text, nullable=True)
    scenario_hint = Column(Text, nullable=True)
    theme_tags = Column(JSON, default=list)  # for gallup: A-side themes
    b_side_themes = Column(JSON, default=list)  # for gallup: B-side themes (choice subtracted)


class CareerMajorMapping(Base):
    __tablename__ = "career_major_mapping"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    career_name = Column(String, nullable=False)
    riasec_primary = Column(String, nullable=False, index=True)
    cs_domain = Column(String, nullable=False, index=True)
    related_majors = Column(JSON, default=list)
    evidence_level = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    career_tag = Column(String, nullable=True)  # steady / explore / challenge


class ThemeDescription(Base):
    __tablename__ = "theme_descriptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    theme_name = Column(String, nullable=False, unique=True, index=True)
    theme_name_en = Column(String, nullable=True)
    domain = Column(String, nullable=False)
    standard_definition = Column(Text, nullable=True)
    feature = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    application = Column(Text, nullable=True)
    blind_spots = Column(Text, nullable=True)
