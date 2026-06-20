import json
import os
from risk_tool.models import Project, RiskResult

GENERAL = "一般危大"
EXCEEDING = "超过一定规模危大"
KEY_SUPERVISION = "重点督办"

ATTR_UNITS = {
    "excavation_depth": "m",
    "scaffold_height": "m",
    "lifting_weight": "t",
}

ATTR_LABELS = {
    "excavation_depth": "开挖深度",
    "scaffold_height": "架体高度",
    "lifting_weight": "吊装重量",
}

MISSING_ITEM_LABELS = {
    "monitoring": "监测措施",
    "emergency_plan": "应急预案",
    "expert_review_date": "专家论证日期",
    "chief_review": "总监审核意见",
}


def load_config(config_path: str = None) -> dict:
    if config_path is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base, "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def classify(project: Project, config: dict) -> RiskResult:
    triggers = []
    level = GENERAL

    general_rules = config.get("general_thresholds", {}).get(project.hazard_type, {})
    exceeding_rules = config.get("exceeding_thresholds", {}).get(project.hazard_type, {})
    key_cfg = config.get("key_supervision", {})
    env_keywords = config.get("complex_env_keywords", [])

    is_general = False
    for attr, limit in general_rules.items():
        val = getattr(project, attr, None)
        if val is not None and val >= limit:
            is_general = True
            label = ATTR_LABELS.get(attr, attr)
            unit = ATTR_UNITS.get(attr, "")
            triggers.append(f"{label}={val}{unit} ≥ 危大阈值{limit}{unit}")

    is_exceeding = False
    default_exceeding = exceeding_rules.get("default_exceeding", False) if isinstance(exceeding_rules, dict) else False

    numeric_exceed = {k: v for k, v in exceeding_rules.items() if k != "default_exceeding"} if isinstance(exceeding_rules, dict) else {}
    if numeric_exceed:
        for attr, limit in numeric_exceed.items():
            val = getattr(project, attr, None)
            if val is not None and val >= limit:
                is_exceeding = True
                label = ATTR_LABELS.get(attr, attr)
                unit = ATTR_UNITS.get(attr, "")
                triggers.append(f"{label}={val}{unit} ≥ 超规模阈值{limit}{unit}")

    if default_exceeding and not numeric_exceed:
        is_exceeding = True
        triggers.append(f"{project.hazard_type}默认属于超过一定规模危大")
    elif default_exceeding and not is_exceeding and is_general:
        is_exceeding = True
        triggers.append(f"{project.hazard_type}默认属于超过一定规模危大")

    if not is_general and not is_exceeding:
        if general_rules or default_exceeding:
            if general_rules:
                for attr, limit in general_rules.items():
                    val = getattr(project, attr, None)
                    if val is not None and val < limit:
                        triggers.append(f"{ATTR_LABELS.get(attr, attr)}={val}{ATTR_UNITS.get(attr, '')} < 危大阈值{limit}{ATTR_UNITS.get(attr, '')}")

    env_complex = _is_env_complex(project.surrounding_env, env_keywords)
    if env_complex:
        triggers.append(f"周边环境复杂: {project.surrounding_env}")

    if is_exceeding:
        level = EXCEEDING
    elif is_general:
        level = GENERAL
    else:
        if default_exceeding:
            level = EXCEEDING
        else:
            level = GENERAL

    is_key = False
    key_reasons = []

    missing_count = _count_missing(project)
    min_missing = key_cfg.get("min_missing_items", 2)
    short_days = key_cfg.get("max_short_duration_days", 15)

    if level == EXCEEDING and missing_count >= min_missing:
        is_key = True
        key_reasons.append(f"超过一定规模且缺项≥{min_missing}项(缺{missing_count}项)")

    if level == EXCEEDING and env_complex:
        is_key = True
        key_reasons.append("超过一定规模且周边环境复杂")

    if project.planned_duration is not None and project.planned_duration < short_days and level == EXCEEDING:
        is_key = True
        key_reasons.append(f"工期极紧(计划{project.planned_duration}天，短于{short_days}天阈值)")

    if is_key:
        level = KEY_SUPERVISION

    missing_items = _detect_missing(project)

    questions = _generate_questions(project, level, env_complex, missing_items, config)

    return RiskResult(
        project_name=project.name,
        region=project.region,
        hazard_type=project.hazard_type,
        level=level,
        triggers=triggers,
        missing_items=missing_items,
        is_key_supervision=is_key,
        key_reasons=key_reasons,
        inspection_questions=questions,
    )


def _is_env_complex(env: str, keywords: list) -> bool:
    if not env:
        return False
    return any(kw in env for kw in keywords)


def _count_missing(project: Project) -> int:
    return sum([
        not project.has_monitoring,
        not project.has_emergency_plan,
        not project.has_expert_review_date,
        not project.has_chief_review,
    ])


def _detect_missing(project: Project) -> list:
    items = []
    if not project.has_monitoring:
        items.append("监测措施")
    if not project.has_emergency_plan:
        items.append("应急预案")
    if not project.has_expert_review_date:
        items.append("专家论证日期")
    if not project.has_chief_review:
        items.append("总监审核意见")
    return items


def _generate_questions(project: Project, level: str, env_complex: bool, missing: list, config: dict) -> list:
    questions_bank = config.get("inspection_questions", {})
    type_questions = questions_bank.get(project.hazard_type, questions_bank.get("其他危大工程", []))

    questions = []

    if level in (EXCEEDING, KEY_SUPERVISION):
        questions.extend(type_questions[:3])

        if env_complex:
            questions.append("周边建(构)筑物及管线保护措施是否落实?第三方监测是否已进场?")

        if "应急预案" in missing:
            questions.append("应急预案缺失,现场应急物资和疏散通道是否具备?")

        if "监测措施" in missing:
            questions.append("监测措施缺失,变形观测点是否已布设?预警阈值是否明确?")

        if "专家论证日期" in missing:
            questions.append("专家论证尚未完成,是否存在先施工后论证的情况?")

        if "总监审核意见" in missing:
            questions.append("总监审核意见缺失,方案审批流程是否闭环?")

        short_days = config.get("key_supervision", {}).get("max_short_duration_days", 15)
        if project.planned_duration is not None and project.planned_duration < short_days:
            questions.append(f"工期仅{project.planned_duration}天,是否存在赶工压缩合理工期的情况?")

    elif level == GENERAL:
        questions.extend(type_questions[:2])
        if "应急预案" in missing:
            questions.append("应急预案缺失,是否编制了应急处置预案?")
        if "监测措施" in missing:
            questions.append("监测措施缺失,现场安全监测是否有安排?")

    seen = set()
    unique = []
    for q in questions:
        if q not in seen:
            seen.add(q)
            unique.append(q)

    if level in (EXCEEDING, KEY_SUPERVISION):
        while len(unique) < 3 and len(type_questions) > len(unique):
            for q in type_questions:
                if q not in seen:
                    seen.add(q)
                    unique.append(q)
                    if len(unique) >= 3:
                        break
        return unique[:5]
    else:
        return unique[:3]
