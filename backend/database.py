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


class RoleInsightRun(Base):
    __tablename__ = "role_insight_runs"

    id = Column(Text, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    status = Column(Text, nullable=False, default="generated")
    methodology_version = Column(Text)
    model = Column(Text)
    raw_input_json = Column(Text)
    output_json = Column(Text, nullable=False)
    ais_composite = Column(Float)
    aps_composite = Column(Float)
    ais_band = Column(Text)
    aps_band = Column(Text)
    aria_classification = Column(Text)
    risk_level = Column(Text)
    generated_at = Column(Text, nullable=False)
    reviewed_at = Column(Text)
    frozen_at = Column(Text)

    role = relationship("Role")

    def to_dict(self, include_output: bool = False):
        payload = {
            "id": self.id,
            "role_id": self.role_id,
            "status": self.status,
            "methodology_version": self.methodology_version,
            "model": self.model,
            "ais_composite": self.ais_composite,
            "aps_composite": self.aps_composite,
            "ais_band": self.ais_band,
            "aps_band": self.aps_band,
            "aria_classification": self.aria_classification,
            "risk_level": self.risk_level,
            "generated_at": self.generated_at,
            "reviewed_at": self.reviewed_at,
            "frozen_at": self.frozen_at,
        }
        if include_output:
            payload["raw_input"] = json.loads(self.raw_input_json) if self.raw_input_json else None
            payload["output"] = json.loads(self.output_json) if self.output_json else None
        return payload


class OrgReportRun(Base):
    __tablename__ = "org_report_runs"

    id = Column(Text, primary_key=True)
    organisation_name = Column(Text, nullable=False)
    organisation_context_json = Column(Text, nullable=False)
    report_config_json = Column(Text, nullable=False)
    role_insight_run_ids = Column(Text, nullable=False)
    aggregate_json = Column(Text, nullable=False)
    output_json = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="generated")
    generated_at = Column(Text, nullable=False)
    reviewed_at = Column(Text)
    frozen_at = Column(Text)

    def to_dict(self, include_output: bool = False):
        payload = {
            "id": self.id,
            "organisation_name": self.organisation_name,
            "status": self.status,
            "role_insight_run_ids": json.loads(self.role_insight_run_ids) if self.role_insight_run_ids else [],
            "generated_at": self.generated_at,
            "reviewed_at": self.reviewed_at,
            "frozen_at": self.frozen_at,
        }
        if include_output:
            payload["organisation_context"] = json.loads(self.organisation_context_json) if self.organisation_context_json else None
            payload["report_config"] = json.loads(self.report_config_json) if self.report_config_json else None
            payload["aggregate"] = json.loads(self.aggregate_json) if self.aggregate_json else None
            payload["output"] = json.loads(self.output_json) if self.output_json else None
        return payload


class ReviewEvent(Base):
    __tablename__ = "review_events"

    id = Column(Text, primary_key=True)
    entity_type = Column(Text, nullable=False)
    entity_id = Column(Text, nullable=False)
    reviewer = Column(Text)
    event_type = Column(Text, nullable=False)
    before_json = Column(Text)
    after_json = Column(Text)
    reason = Column(Text)
    created_at = Column(Text, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "reviewer": self.reviewer,
            "event_type": self.event_type,
            "before": json.loads(self.before_json) if self.before_json else None,
            "after": json.loads(self.after_json) if self.after_json else None,
            "reason": self.reason,
            "created_at": self.created_at,
        }


class RenderedArtifact(Base):
    __tablename__ = "rendered_artifacts"

    id = Column(Text, primary_key=True)
    report_run_id = Column(Text, nullable=False)
    report_run_type = Column(Text, nullable=False)
    renderer_name = Column(Text, nullable=False)
    visual_style_id = Column(Text, nullable=False)
    output_format = Column(Text, nullable=False)
    file_path = Column(Text, nullable=False)
    content_hash = Column(Text, nullable=False)
    generated_at = Column(Text, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "report_run_id": self.report_run_id,
            "report_run_type": self.report_run_type,
            "renderer_name": self.renderer_name,
            "visual_style_id": self.visual_style_id,
            "output_format": self.output_format,
            "file_path": self.file_path,
            "content_hash": self.content_hash,
            "generated_at": self.generated_at,
        }


class RoleTask(Base):
    __tablename__ = "role_tasks"

    id = Column(Text, primary_key=True)
    role_insight_run_id = Column(Text, ForeignKey("role_insight_runs.id"), nullable=False)
    task_id = Column(Text, nullable=False)
    task_name = Column(Text, nullable=False)
    category = Column(Text)
    ais_score = Column(Integer)
    aps_score = Column(Integer)
    rationale = Column(Text)
    order_index = Column(Integer)


class AISVariableScore(Base):
    __tablename__ = "ais_variable_scores"

    id = Column(Text, primary_key=True)
    role_insight_run_id = Column(Text, ForeignKey("role_insight_runs.id"), nullable=False)
    variable_name = Column(Text, nullable=False)
    raw_score = Column(Integer)
    adjusted_score = Column(Integer)
    weight = Column(Float)
    weighted_score = Column(Float)
    justification = Column(Text)
    confidence = Column(Text)


class APSVariableScore(Base):
    __tablename__ = "aps_variable_scores"

    id = Column(Text, primary_key=True)
    role_insight_run_id = Column(Text, ForeignKey("role_insight_runs.id"), nullable=False)
    variable_name = Column(Text, nullable=False)
    score = Column(Integer)
    weight = Column(Float)
    weighted_score = Column(Float)
    justification = Column(Text)
    confidence = Column(Text)


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Text, primary_key=True)
    canonical_name = Column(Text, nullable=False)
    skill_type = Column(Text, nullable=False)
    description = Column(Text)


class TaskSkillMapping(Base):
    __tablename__ = "task_skill_mappings"

    id = Column(Text, primary_key=True)
    role_insight_run_id = Column(Text, ForeignKey("role_insight_runs.id"), nullable=False)
    task_id = Column(Text, nullable=False)
    skill_id = Column(Text, ForeignKey("skills.id"), nullable=False)


class TaskEvolutionMapping(Base):
    __tablename__ = "task_evolution_mappings"

    id = Column(Text, primary_key=True)
    role_insight_run_id = Column(Text, ForeignKey("role_insight_runs.id"), nullable=False)
    task_id = Column(Text, nullable=False)
    how_ai_changes_this = Column(Text)
    human_role_in_future_state = Column(Text)


class RoleRecommendation(Base):
    __tablename__ = "role_recommendations"

    id = Column(Text, primary_key=True)
    role_insight_run_id = Column(Text, ForeignKey("role_insight_runs.id"), nullable=False)
    audience = Column(Text, nullable=False)
    recommendation_text = Column(Text)


class SourceFact(Base):
    __tablename__ = "source_facts"

    id = Column(Text, primary_key=True)
    run_id = Column(Text, nullable=False)
    run_type = Column(Text, nullable=False)
    source_type = Column(Text, nullable=False)
    source_ref = Column(Text)
    fact_text = Column(Text, nullable=False)
    normalized_value_json = Column(Text)


class GroundedClaim(Base):
    __tablename__ = "grounded_claims"

    id = Column(Text, primary_key=True)
    run_id = Column(Text, nullable=False)
    run_type = Column(Text, nullable=False)
    claim_type = Column(Text, nullable=False)
    claim_text = Column(Text)
    confidence = Column(Text)
    limitations_json = Column(Text)
    inference_trace_json = Column(Text)


class ClaimSourceFact(Base):
    __tablename__ = "claim_source_facts"

    claim_id = Column(Text, ForeignKey("grounded_claims.id"), primary_key=True)
    source_fact_id = Column(Text, ForeignKey("source_facts.id"), primary_key=True)


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
    # Lightweight migrations for the local SQLite MVP.
    with engine.connect() as conn:
        from sqlalchemy import text, inspect
        inspector = inspect(engine)
        role_columns = [c["name"] for c in inspector.get_columns("roles")]
        if "recommendations" not in role_columns:
            conn.execute(text("ALTER TABLE roles ADD COLUMN recommendations TEXT"))
            conn.commit()
        if "org_report_runs" in inspector.get_table_names():
            org_columns = [c["name"] for c in inspector.get_columns("org_report_runs")]
            if "reviewed_at" not in org_columns:
                conn.execute(text("ALTER TABLE org_report_runs ADD COLUMN reviewed_at TEXT"))
                conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
