"""ARIA classification logic — pure Python, no LLM calls."""

from dataclasses import dataclass

# AIS weights
AIS_WEIGHTS = {
    "cognitive_routine_level": 0.25,
    "data_dependency": 0.20,
    "process_repeatability": 0.20,
    "social_perception": 0.15,
    "physical_complexity": 0.10,
    "regulatory_accountability": 0.10,
}

AIS_INVERSE = {"social_perception", "physical_complexity", "regulatory_accountability"}

# APS weights
APS_WEIGHTS = {
    "knowledge_processing": 0.25,
    "output_sensitivity": 0.25,
    "decision_support": 0.20,
    "repetitive_cognitive": 0.20,
    "communication_volume": 0.10,
}

# Matrix: (ais_band, aps_band) -> classification
MATRIX = {
    ("high", "high"): "Transform",
    ("high", "medium"): "Accelerate",
    ("high", "low"): "Transition",
    ("medium", "high"): "Optimize",
    ("medium", "medium"): "Adapt",
    ("medium", "low"): "Monitor",
    ("low", "high"): "Expand",
    ("low", "medium"): "Invest selectively",
    ("low", "low"): "Maintain",
}

AIS_VARIABLE_NAMES = {
    "cognitive_routine_level": "Cognitive routine level",
    "data_dependency": "Data dependency",
    "process_repeatability": "Process repeatability",
    "social_perception": "Social perception",
    "physical_complexity": "Physical complexity",
    "regulatory_accountability": "Regulatory accountability",
}

AIS_VARIABLE_CODES = {
    "cognitive_routine_level": "crl",
    "data_dependency": "dds",
    "process_repeatability": "prv",
    "social_perception": "sp",
    "physical_complexity": "pc",
    "regulatory_accountability": "ra",
}

APS_VARIABLE_NAMES = {
    "knowledge_processing": "Knowledge processing",
    "output_sensitivity": "Output sensitivity",
    "decision_support": "Decision support",
    "repetitive_cognitive": "Repetitive cognitive",
    "communication_volume": "Communication volume",
}

APS_VARIABLE_CODES = {
    "knowledge_processing": "kip",
    "output_sensitivity": "oqv",
    "decision_support": "dsr",
    "repetitive_cognitive": "rcw",
    "communication_volume": "ccv",
}


def band(score: float) -> str:
    if score < 45:
        return "low"
    elif score < 65:
        return "medium"
    else:
        return "high"


def risk_level(ais: float) -> str:
    if ais >= 75:
        return "Very high"
    elif ais >= 60:
        return "High"
    elif ais >= 45:
        return "Moderate"
    elif ais >= 30:
        return "Low"
    else:
        return "Very low"


@dataclass
class AISVariableResult:
    variable: str
    name: str
    raw_score: int
    is_inverse: bool
    adjusted: int
    weight: float
    weighted: float
    rationale: str


@dataclass
class APSVariableResult:
    variable: str
    name: str
    score: int
    weight: float
    weighted: float
    rationale: str


@dataclass
class ClassificationResult:
    ais_composite: float
    aps_composite: float
    ais_band: str
    aps_band: str
    classification: str
    risk_level: str
    ais_variables: list[AISVariableResult]
    aps_variables: list[APSVariableResult]


def classify(role_analysis) -> ClassificationResult:
    """Takes a BAML RoleAnalysis and computes the full ARIA classification."""
    ais = role_analysis.ais
    aps = role_analysis.aps

    # Compute AIS variables
    ais_vars = []
    ais_composite = 0.0
    for var_name, weight in AIS_WEIGHTS.items():
        vs = getattr(ais, var_name)
        raw = vs.score
        is_inv = var_name in AIS_INVERSE
        adjusted = (100 - raw) if is_inv else raw
        weighted = adjusted * weight
        ais_composite += weighted
        ais_vars.append(AISVariableResult(
            variable=AIS_VARIABLE_CODES[var_name],
            name=AIS_VARIABLE_NAMES[var_name],
            raw_score=raw,
            is_inverse=is_inv,
            adjusted=adjusted,
            weight=weight,
            weighted=round(weighted, 2),
            rationale=vs.justification,
        ))

    # Compute APS variables
    aps_vars = []
    aps_composite = 0.0
    for var_name, weight in APS_WEIGHTS.items():
        vs = getattr(aps, var_name)
        raw = vs.score
        weighted = raw * weight
        aps_composite += weighted
        aps_vars.append(APSVariableResult(
            variable=APS_VARIABLE_CODES[var_name],
            name=APS_VARIABLE_NAMES[var_name],
            score=raw,
            weight=weight,
            weighted=round(weighted, 2),
            rationale=vs.justification,
        ))

    ais_composite = round(ais_composite, 2)
    aps_composite = round(aps_composite, 2)
    ais_b = band(ais_composite)
    aps_b = band(aps_composite)

    return ClassificationResult(
        ais_composite=ais_composite,
        aps_composite=aps_composite,
        ais_band=ais_b,
        aps_band=aps_b,
        classification=MATRIX[(ais_b, aps_b)],
        risk_level=risk_level(ais_composite),
        ais_variables=ais_vars,
        aps_variables=aps_vars,
    )
