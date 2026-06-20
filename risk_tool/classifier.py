from risk_tool.models import Project, RiskResult

GENERAL = "一般危大"
EXCEEDING = "超过一定规模危大"
KEY_SUPERVISION = "重点督办"

HAZARD_TYPES = [
    "深基坑工程",
    "模板工程及支撑体系",
    "起重吊装及安拆工程",
    "脚手架工程",
    "拆除工程",
    "暗挖工程",
    "其他危大工程",
]

THRESHOLDS = {
    "深基坑工程": {
        "general": {"excavation_depth": 3.0},
        "exceeding": {"excavation_depth": 5.0},
    },
    "模板工程及支撑体系": {
        "general": {"scaffold_height": 5.0},
        "exceeding": {"scaffold_height": 8.0},
    },
    "起重吊装及安拆工程": {
        "general": {"lifting_weight": 1.0},
        "exceeding": {"lifting_weight": 10.0},
    },
    "脚手架工程": {
        "general": {"scaffold_height": 24.0},
        "exceeding": {"scaffold_height": 50.0},
    },
    "拆除工程": {
        "general": {},
        "exceeding": {},
    },
    "暗挖工程": {
        "general": {},
        "exceeding": {},
    },
    "其他危大工程": {
        "general": {},
        "exceeding": {},
    },
}

COMPLEX_ENV_KEYWORDS = ["密集", "临近建筑", "管线", "地铁", "铁路", "河道", "边坡", "软土", "液化", "采空"]


def _check_threshold(project: Project, threshold: dict) -> bool:
    for key, limit in threshold.items():
        val = getattr(project, key, None)
        if val is not None and val >= limit:
            return True
    return False


def _is_env_complex(env: str) -> bool:
    return any(kw in env for kw in COMPLEX_ENV_KEYWORDS)


def classify(project: Project) -> RiskResult:
    triggers = []
    level = GENERAL

    rules = THRESHOLDS.get(project.hazard_type, THRESHOLDS["其他危大工程"])

    if rules["general"]:
        for attr, limit in rules["general"].items():
            val = getattr(project, attr, None)
            if val is not None and val >= limit:
                triggers.append(f"{attr}={val}{_unit(attr)} ≥ 规定值{limit}{_unit(attr)}")

    if rules["exceeding"]:
        if _check_threshold(project, rules["exceeding"]):
            level = EXCEEDING
            for attr, limit in rules["exceeding"].items():
                val = getattr(project, attr, None)
                if val is not None and val >= limit:
                    triggers.append(f"{attr}={val}{_unit(attr)} ≥ 超规模阈值{limit}{_unit(attr)}")
    else:
        if project.hazard_type in ("拆除工程", "暗挖工程"):
            level = EXCEEDING
            triggers.append(f"{project.hazard_type}默认属于超过一定规模危大")

    env_complex = _is_env_complex(project.surrounding_env)
    if env_complex:
        triggers.append(f"周边环境复杂: {project.surrounding_env}")

    is_key = False
    key_reasons = []

    missing_count = _count_missing(project)
    if level == EXCEEDING and missing_count >= 2:
        is_key = True
        key_reasons.append(f"超过一定规模且缺项≥2项(缺{missing_count}项)")

    if level == EXCEEDING and env_complex:
        is_key = True
        key_reasons.append("超过一定规模且周边环境复杂")

    if project.planned_duration is not None and project.planned_duration < 15 and level == EXCEEDING:
        is_key = True
        key_reasons.append(f"工期极紧(计划{project.planned_duration}天)")

    if is_key:
        level = KEY_SUPERVISION

    missing_items = _detect_missing(project)

    questions = _generate_questions(project, level, env_complex, missing_items)

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


def _unit(attr: str) -> str:
    return {"excavation_depth": "m", "scaffold_height": "m", "lifting_weight": "t"}.get(attr, "")


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


def _generate_questions(project: Project, level: str, env_complex: bool, missing: list) -> list:
    questions = []
    if level in (EXCEEDING, KEY_SUPERVISION):
        if project.excavation_depth and project.excavation_depth >= 5:
            questions.append("深基坑支护方案是否经专家论证?现场实际开挖深度与方案是否一致?")
        if project.scaffold_height and project.scaffold_height >= 8:
            questions.append("高大模板支撑体系搭设验收记录是否齐全?扫地杆、剪刀撑是否按方案设置?")
        if project.lifting_weight and project.lifting_weight >= 10:
            questions.append("起重机械特种设备使用登记证是否有效?吊装作业专项方案是否覆盖全过程?")
        if env_complex:
            questions.append("周边建(构)筑物及管线保护措施是否落实?第三方监测是否已进场?")
        if "应急预案" in missing:
            questions.append("应急预案缺失,现场应急物资和疏散通道是否具备?")
        if "监测措施" in missing:
            questions.append("监测措施缺失,变形观测点是否已布设?预警阈值是否明确?")
        if project.planned_duration and project.planned_duration < 15:
            questions.append(f"工期仅{project.planned_duration}天,是否存在赶工压缩合理工期的情况?")
    if level == GENERAL:
        if project.excavation_depth and project.excavation_depth >= 3:
            questions.append("基坑临边防护及排水措施是否到位?")
        if project.scaffold_height and project.scaffold_height >= 5:
            questions.append("模板支撑体系是否经验收合格?")
    seen = set()
    unique = []
    for q in questions:
        if q not in seen:
            seen.add(q)
            unique.append(q)
    return unique[:5]
