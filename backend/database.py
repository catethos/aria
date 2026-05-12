"""SQLite database setup with SQLAlchemy."""

import json
from sqlalchemy import create_engine, Column, Integer, Text, Float, Boolean, ForeignKey, func
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = "sqlite:///aria.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    department = Column(Text)
    grade = Column(Text)
    headcount = Column(Integer, default=1)
    description = Column(Text, nullable=False)
    tasks = Column(Text)  # JSON array
    ais_composite = Column(Float)
    aps_composite = Column(Float)
    classification = Column(Text)
    ais_band = Column(Text)
    aps_band = Column(Text)
    risk_level = Column(Text)
    recommendations = Column(Text)  # JSON: RoleRecommendations

    ais_variables = relationship("AISVariable", back_populates="role", cascade="all, delete-orphan")
    aps_variables = relationship("APSVariable", back_populates="role", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "department": self.department,
            "grade": self.grade,
            "headcount": self.headcount,
            "description": self.description,
            "tasks": json.loads(self.tasks) if self.tasks else [],
            "ais_composite": self.ais_composite,
            "aps_composite": self.aps_composite,
            "classification": self.classification,
            "ais_band": self.ais_band,
            "aps_band": self.aps_band,
            "risk_level": self.risk_level,
            "recommendations": json.loads(self.recommendations) if self.recommendations else None,
        }

    def to_detail_dict(self):
        d = self.to_dict()
        d["ais_variables"] = [v.to_dict() for v in self.ais_variables]
        d["aps_variables"] = [v.to_dict() for v in self.aps_variables]
        return d


class AISVariable(Base):
    __tablename__ = "ais_variables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    variable = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    raw_score = Column(Integer)
    is_inverse = Column(Boolean)
    adjusted = Column(Integer)
    weight = Column(Float)
    weighted = Column(Float)
    rationale = Column(Text)

    role = relationship("Role", back_populates="ais_variables")

    def to_dict(self):
        return {
            "variable": self.variable,
            "name": self.name,
            "raw_score": self.raw_score,
            "is_inverse": self.is_inverse,
            "adjusted": self.adjusted,
            "weight": self.weight,
            "weighted": self.weighted,
            "rationale": self.rationale,
        }


class APSVariable(Base):
    __tablename__ = "aps_variables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    variable = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    score = Column(Integer)
    weight = Column(Float)
    weighted = Column(Float)
    rationale = Column(Text)

    role = relationship("Role", back_populates="aps_variables")

    def to_dict(self):
        return {
            "variable": self.variable,
            "name": self.name,
            "score": self.score,
            "weight": self.weight,
            "weighted": self.weighted,
            "rationale": self.rationale,
        }


def init_db():
    Base.metadata.create_all(bind=engine)
    # Migrate: add recommendations column if missing
    with engine.connect() as conn:
        from sqlalchemy import text, inspect
        inspector = inspect(engine)
        columns = [c["name"] for c in inspector.get_columns("roles")]
        if "recommendations" not in columns:
            conn.execute(text("ALTER TABLE roles ADD COLUMN recommendations TEXT"))
            conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
