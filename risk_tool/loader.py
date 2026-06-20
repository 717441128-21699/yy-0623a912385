import json
from typing import List
from risk_tool.models import Project, RiskResult
from risk_tool.classifier import classify


def load_projects(filepath: str) -> List[Project]:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    projects = []
    for item in data:
        projects.append(Project(
            name=item.get("name", ""),
            region=item.get("region", ""),
            hazard_type=item.get("hazard_type", "其他危大工程"),
            scale_params=item.get("scale_params", {}),
            excavation_depth=item.get("excavation_depth"),
            scaffold_height=item.get("scaffold_height"),
            lifting_weight=item.get("lifting_weight"),
            surrounding_env=item.get("surrounding_env", ""),
            planned_duration=item.get("planned_duration"),
            has_monitoring=item.get("has_monitoring", False),
            has_emergency_plan=item.get("has_emergency_plan", False),
            has_expert_review_date=item.get("has_expert_review_date", False),
            has_chief_review=item.get("has_chief_review", False),
        ))
    return projects


def filter_projects(projects: List[Project], name: str = None, region: str = None) -> List[Project]:
    result = projects
    if name:
        result = [p for p in result if name in p.name]
    if region:
        result = [p for p in result if region in p.region]
    return result


def evaluate(projects: List[Project]) -> List[RiskResult]:
    return [classify(p) for p in projects]
