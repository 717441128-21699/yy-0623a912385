from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Project:
    name: str
    region: str
    hazard_type: str
    scale_params: dict = field(default_factory=dict)
    excavation_depth: Optional[float] = None
    scaffold_height: Optional[float] = None
    lifting_weight: Optional[float] = None
    surrounding_env: str = ""
    planned_duration: Optional[int] = None
    has_monitoring: bool = False
    has_emergency_plan: bool = False
    has_expert_review_date: bool = False
    has_chief_review: bool = False


@dataclass
class RiskResult:
    project_name: str
    region: str
    hazard_type: str
    level: str
    triggers: list = field(default_factory=list)
    missing_items: list = field(default_factory=list)
    is_key_supervision: bool = False
    key_reasons: list = field(default_factory=list)
    inspection_questions: list = field(default_factory=list)
