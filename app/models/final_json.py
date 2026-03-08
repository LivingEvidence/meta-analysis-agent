from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class StudyResult(BaseModel):
    study: str
    year: int | None = None
    effect: float
    ci_lower: float
    ci_upper: float
    weight: float  # percentage
    se: float | None = None
    et: int | None = None
    nt: int | None = None
    ec: int | None = None
    nc: int | None = None


class PooledEstimate(BaseModel):
    model: str  # "random" or "fixed"
    effect: float
    ci_lower: float
    ci_upper: float
    z_value: float | None = None
    p_value: float


class Heterogeneity(BaseModel):
    tau2: float
    i2: float
    q_statistic: float
    q_df: int
    q_pvalue: float
    prediction_lower: float | None = None
    prediction_upper: float | None = None


class PublicationBias(BaseModel):
    method: str  # "Egger"
    statistic: float | None = None
    p_value: float | None = None
    note: str | None = None


class LeaveOneOut(BaseModel):
    excluded_study: str
    effect: float
    ci_lower: float
    ci_upper: float


class OutcomeAnalysis(BaseModel):
    outcome_name: str
    full_name: str
    measure: str
    data_type: str
    is_ratio: bool
    n_studies: int
    studies: list[StudyResult]
    pooled_random: PooledEstimate
    pooled_fixed: PooledEstimate
    heterogeneity: Heterogeneity
    publication_bias: PublicationBias
    leave_one_out: list[LeaveOneOut]
    figures: dict[str, str]  # e.g. {"forest_plot": "figures/OS/forest_plot.png"}
    interpretation: str | None = None


class FinalJSON(BaseModel):
    session_id: str
    request_id: str
    created_at: str  # ISO 8601
    outcomes: list[OutcomeAnalysis]
    metadata: dict[str, Any] = {}
