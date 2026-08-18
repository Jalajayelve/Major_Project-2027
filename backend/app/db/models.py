from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(Integer, primary_key=True)
    program_type = Column(String(20), nullable=False)
    gpa = Column(Float, nullable=False)
    gre_score = Column(Float, nullable=True)
    gmat_score = Column(Float, nullable=True)
    work_experience = Column(Float, nullable=True)
    research_experience = Column(Float, nullable=True)
    essay_score = Column(Float, nullable=True)


class UniversityMatch(Base):
    __tablename__ = "university_matches"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, nullable=False)
    university_name = Column(String(200), nullable=False)
    tier = Column(String(50), nullable=False)
