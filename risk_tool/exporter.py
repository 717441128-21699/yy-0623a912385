import csv
import os
from datetime import datetime
from typing import List
from risk_tool.models import RiskResult
from risk_tool.classifier import KEY_SUPERVISION, EXCEEDING, GENERAL


def _date_str() -> str:
    return datetime.now().strftime("%Y%m%d")


def _region_summary(results: List[RiskResult]) -> dict:
    from collections import defaultdict
    stats = defaultdict(lambda: {"total": 0, GENERAL: 0, EXCEEDING: 0, KEY_SUPERVISION: 0, "missing": 0})
    for r in results:
        s = stats[r.region]
        s["total"] += 1
        s[r.level] += 1
        if r.missing_items:
            s["missing"] += 1
    return dict(stats)


def export_markdown(results: List[RiskResult], output_dir: str = None) -> str:
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(output_dir, exist_ok=True)

    fname = f"危大工程风险评分报告_{_date_str()}.md"
    fpath = os.path.join(output_dir, fname)

    general_n = sum(1 for r in results if r.level == GENERAL)
    exceed_n = sum(1 for r in results if r.level == EXCEEDING)
    key_n = sum(1 for r in results if r.level == KEY_SUPERVISION)
    missing_n = sum(1 for r in results if r.missing_items)

    lines = []
    lines.append(f"# 危大工程方案风险评分报告")
    lines.append("")
    lines.append(f"> 生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"> 项目总数: {len(results)} 个")
    lines.append(f"> 一般危大: {general_n} 个 | 超过一定规模: {exceed_n} 个 | 重点督办: **{key_n}** 个 | 存在缺项: {missing_n} 个")
    lines.append("")

    region_stats = _region_summary(results)
    if len(region_stats) > 1:
        lines.append("## 区域汇总")
        lines.append("")
        lines.append("| 区域 | 总数 | 一般危大 | 超过一定规模 | 重点督办 | 缺项数 |")
        lines.append("|------|-----:|---------:|-------------:|---------:|-------:|")
        for region in sorted(region_stats.keys()):
            s = region_stats[region]
            lines.append(f"| {region} | {s['total']} | {s[GENERAL]} | {s[EXCEEDING]} | **{s[KEY_SUPERVISION]}** | {s['missing']} |")
        lines.append("")

    lines.append("## 项目评分明细")
    lines.append("")
    for i, r in enumerate(results, 1):
        level_md = f"**{r.level}**" if r.level == KEY_SUPERVISION else r.level
        lines.append(f"### {i}. {r.project_name} ({r.region})")
        lines.append("")
        lines.append(f"- 工程类型: {r.hazard_type}")
        lines.append(f"- 风险等级: {level_md}")
        if r.triggers:
            lines.append(f"- 触发原因:")
            for t in r.triggers:
                lines.append(f"  - {t}")
        if r.missing_items:
            lines.append(f"- 缺项提示: {', '.join(r.missing_items)}")
        if r.is_key_supervision and r.key_reasons:
            lines.append(f"- 重点督办原因:")
            for reason in r.key_reasons:
                lines.append(f"  - {reason}")
        if r.inspection_questions:
            lines.append(f"- 现场追问 ({len(r.inspection_questions)}条):")
            for j, q in enumerate(r.inspection_questions, 1):
                lines.append(f"  {j}. {q}")
        lines.append("")

    high_risk = [r for r in results if r.level in (EXCEEDING, KEY_SUPERVISION)]
    if high_risk:
        lines.append("## 巡检核查清单")
        lines.append("")
        lines.append(f"共 **{len(high_risk)}** 个高风险项目需重点核查:")
        lines.append("")
        for i, r in enumerate(high_risk, 1):
            lines.append(f"### {i}. {r.project_name}")
            lines.append("")
            lines.append(f"- 区域/类型: {r.region} / {r.hazard_type}")
            lines.append(f"- 等级: {r.level}")
            if r.missing_items:
                lines.append(f"- 缺项: {', '.join(r.missing_items)}")
            lines.append(f"- 现场追问:")
            for j, q in enumerate(r.inspection_questions, 1):
                lines.append(f"  {j}. {q}")
            lines.append("")

    with open(fpath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return fpath


def export_csv(results: List[RiskResult], output_dir: str = None) -> str:
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(output_dir, exist_ok=True)

    fname = f"危大工程风险评分报告_{_date_str()}.csv"
    fpath = os.path.join(output_dir, fname)

    headers = [
        "序号", "项目名称", "区域", "工程类型", "风险等级",
        "触发原因", "缺项", "重点督办原因", "现场追问",
        "开挖深度(m)", "架体高度(m)", "吊装重量(t)",
        "周边环境", "计划工期(天)",
    ]

    with open(fpath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for i, r in enumerate(results, 1):
            writer.writerow([
                i,
                r.project_name,
                r.region,
                r.hazard_type,
                r.level,
                "; ".join(r.triggers),
                "; ".join(r.missing_items),
                "; ".join(r.key_reasons),
                " | ".join(r.inspection_questions),
                "", "", "",
                "", "",
            ])

    return fpath


def export_inspection_csv(results: List[RiskResult], output_dir: str = None) -> str:
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(output_dir, exist_ok=True)

    high_risk = [r for r in results if r.level in (EXCEEDING, KEY_SUPERVISION)]
    fname = f"巡检核查清单_{_date_str()}.csv"
    fpath = os.path.join(output_dir, fname)

    headers = [
        "序号", "项目名称", "区域", "工程类型", "风险等级",
        "判定依据", "缺项", "重点督办原因",
        "追问1", "追问2", "追问3", "追问4", "追问5",
    ]

    with open(fpath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for i, r in enumerate(high_risk, 1):
            qs = r.inspection_questions + [""] * (5 - len(r.inspection_questions))
            writer.writerow([
                i,
                r.project_name,
                r.region,
                r.hazard_type,
                r.level,
                "; ".join(r.triggers[:3]),
                "; ".join(r.missing_items),
                "; ".join(r.key_reasons),
                qs[0], qs[1], qs[2], qs[3], qs[4],
            ])

    return fpath


def export_weekly_markdown(results: List[RiskResult], top_per_region: int = 3, output_dir: str = None) -> str:
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(output_dir, exist_ok=True)

    fname = f"危大工程周报_{_date_str()}.md"
    fpath = os.path.join(output_dir, fname)

    from risk_tool.report import group_by_region, sort_by_priority

    general_n = sum(1 for r in results if r.level == GENERAL)
    exceed_n = sum(1 for r in results if r.level == EXCEEDING)
    key_n = sum(1 for r in results if r.level == KEY_SUPERVISION)
    missing_n = sum(1 for r in results if r.missing_items)

    today = datetime.now().strftime("%Y-%m-%d")
    lines = []
    lines.append(f"# 危大工程周报 - 重点项目清单")
    lines.append("")
    lines.append(f"> 报告日期: {today}")
    lines.append(f"> 项目总数: {len(results)} 个")
    lines.append(f"> 一般危大: {general_n} | 超过一定规模: {exceed_n} | **重点督办: {key_n}** | 缺项: {missing_n}")
    lines.append("")

    region_stats = _region_summary(results)
    if len(region_stats) > 1:
        lines.append("## 区域汇总")
        lines.append("")
        lines.append("| 区域 | 总数 | 一般危大 | 超过一定规模 | 重点督办 | 缺项数 |")
        lines.append("|------|-----:|---------:|-------------:|---------:|-------:|")
        for region in sorted(region_stats.keys()):
            s = region_stats[region]
            lines.append(f"| {region} | {s['total']} | {s[GENERAL]} | {s[EXCEEDING]} | **{s[KEY_SUPERVISION]}** | {s['missing']} |")
        lines.append("")

    lines.append("## 各区域重点项目（按风险排序）")
    lines.append("")

    grouped = group_by_region(results)
    for region in sorted(grouped.keys()):
        items = grouped[region]
        key_count = sum(1 for r in items if r.level == KEY_SUPERVISION)
        exceed_count = sum(1 for r in items if r.level == EXCEEDING)

        lines.append(f"### {region}")
        lines.append("")
        lines.append(f"> 共 {len(items)} 项 | 重点督办 **{key_count}** 项 | 超过规模 {exceed_count} 项")
        lines.append("")

        top_items = items[:top_per_region]
        for i, r in enumerate(top_items, 1):
            level_label = f"**{r.level}**" if r.level == KEY_SUPERVISION else r.level
            missing_tag = f" 🔴 缺{len(r.missing_items)}项" if r.missing_items else ""
            lines.append(f"**{i}. {r.project_name}** - {level_label}{missing_tag}")
            lines.append(f"- 类型: {r.hazard_type}")
            if r.key_reasons:
                lines.append(f"- 重点原因: {r.key_reasons[0]}")
            elif r.triggers:
                lines.append(f"- 主要触发: {r.triggers[0]}")
            if r.inspection_questions:
                lines.append(f"- 重点追问: {r.inspection_questions[0]}")
            lines.append("")

        if len(items) > top_per_region:
            rest = items[top_per_region:]
            rest_summary = "、".join(r.project_name for r in rest)
            lines.append(f"> 其余项目: {rest_summary}")
            lines.append("")

    all_key = [r for r in results if r.level == KEY_SUPERVISION]
    if all_key:
        lines.append("## 全集团重点督办项目清单")
        lines.append("")
        lines.append("| 序号 | 项目名称 | 区域 | 工程类型 | 重点督办原因 | 缺项 |")
        lines.append("|-----:|----------|------|----------|-------------|------|")
        for i, r in enumerate(sort_by_priority(all_key), 1):
            reasons = "；".join(r.key_reasons[:2]) if r.key_reasons else "-"
            missing = "、".join(r.missing_items) if r.missing_items else "-"
            lines.append(f"| {i} | {r.project_name} | {r.region} | {r.hazard_type} | {reasons} | {missing} |")
        lines.append("")

    lines.append("## 巡检追问要点")
    lines.append("")
    high_risk = [r for r in results if r.level in (EXCEEDING, KEY_SUPERVISION)]
    for i, r in enumerate(sort_by_priority(high_risk), 1):
        lines.append(f"### {i}. {r.project_name} ({r.region})")
        lines.append("")
        lines.append(f"- 等级: {r.level}")
        lines.append(f"- 类型: {r.hazard_type}")
        if r.missing_items:
            lines.append(f"- 缺项: {', '.join(r.missing_items)}")
        if r.key_reasons:
            lines.append(f"- 判定依据: {'; '.join(r.key_reasons)}")
        elif r.triggers:
            lines.append(f"- 判定依据: {'; '.join(r.triggers[:2])}")
        lines.append(f"- 现场追问:")
        for j, q in enumerate(r.inspection_questions, 1):
            lines.append(f"  {j}. {q}")
        lines.append("")

    with open(fpath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return fpath


def export(results: List[RiskResult], fmt: str = "markdown", output_dir: str = None,
           top_per_region: int = 3) -> list:
    fmt = fmt.lower()
    exported = []
    if fmt in ("md", "markdown"):
        exported.append(export_markdown(results, output_dir))
    elif fmt == "weekly":
        exported.append(export_weekly_markdown(results, top_per_region, output_dir))
    elif fmt == "csv":
        exported.append(export_csv(results, output_dir))
        exported.append(export_inspection_csv(results, output_dir))
    elif fmt == "all":
        exported.append(export_markdown(results, output_dir))
        exported.append(export_weekly_markdown(results, top_per_region, output_dir))
        exported.append(export_csv(results, output_dir))
        exported.append(export_inspection_csv(results, output_dir))
    else:
        raise ValueError(f"不支持的导出格式: {fmt}")
    return exported
