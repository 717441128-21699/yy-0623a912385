from typing import List, Dict
from collections import defaultdict
from risk_tool.models import RiskResult
from risk_tool.classifier import KEY_SUPERVISION, EXCEEDING, GENERAL


LEVEL_ICONS = {
    GENERAL: "●",
    EXCEEDING: "▲",
    KEY_SUPERVISION: "★★★",
}

LEVEL_COLORS = {
    GENERAL: "\033[92m",
    EXCEEDING: "\033[93m",
    KEY_SUPERVISION: "\033[91m",
}

RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"
DIM = "\033[2m"
RED = "\033[91m"
YELLOW = "\033[93m"


def _summarize_by_region(results: List[RiskResult]) -> Dict[str, dict]:
    region_stats = defaultdict(lambda: {"total": 0, GENERAL: 0, EXCEEDING: 0, KEY_SUPERVISION: 0, "missing": 0})
    for r in results:
        s = region_stats[r.region]
        s["total"] += 1
        s[r.level] += 1
        if r.missing_items:
            s["missing"] += 1
    return dict(region_stats)


def print_results(results: List[RiskResult], verbose: bool = True):
    if not results:
        print(f"\n{DIM}未找到匹配的项目。{RESET}")
        return

    print(f"\n{'='*60}")
    print(f"{BOLD}  危大工程方案风险评分报告{RESET}")
    print(f"{'='*60}")

    if verbose:
        for i, r in enumerate(results, 1):
            color = LEVEL_COLORS.get(r.level, "")
            icon = LEVEL_ICONS.get(r.level, "○")
            print(f"\n{BOLD}[{i}] {r.project_name}{RESET}  {DIM}({r.region}){RESET}")
            print(f"    工程类型: {r.hazard_type}")
            print(f"    风险等级: {color}{icon} {r.level}{RESET}")

            if r.triggers:
                print(f"    触发原因:")
                for t in r.triggers:
                    print(f"      → {t}")

            if r.missing_items:
                print(f"    {RED}缺项提示:{RESET}")
                for item in r.missing_items:
                    print(f"      ✖ 缺少: {item}")

            if r.is_key_supervision:
                print(f"    {RED}{BOLD}★ 重点督办原因:{RESET}")
                for reason in r.key_reasons:
                    print(f"      → {reason}")

    print(f"\n{'-'*60}")
    print(f"{BOLD}  总体统计{RESET}")
    print(f"{'-'*60}")

    general = [r for r in results if r.level == GENERAL]
    exceeding = [r for r in results if r.level == EXCEEDING]
    key = [r for r in results if r.level == KEY_SUPERVISION]

    print(f"  项目总数:   {len(results)}个")
    print(f"  一般危大:   {len(general)}个")
    print(f"  超过规模:   {len(exceeding)}个")
    print(f"  重点督办:   {RED}{BOLD}{len(key)}个{RESET}")

    any_missing = [r for r in results if r.missing_items]
    if any_missing:
        print(f"  存在缺项:   {YELLOW}{len(any_missing)}个{RESET}")

    region_stats = _summarize_by_region(results)
    if len(region_stats) > 1 or any(any_missing):
        print(f"\n{'-'*60}")
        print(f"{BOLD}  区域汇总{RESET}")
        print(f"{'-'*60}")
        print(f"  {'区域':<12}{'总数':>5}{'一般':>6}{'超规模':>7}{'重点督办':>8}{'缺项':>6}")
        print(f"  {'-'*50}")
        for region in sorted(region_stats.keys()):
            s = region_stats[region]
            key_str = f"{RED}{BOLD}{s[KEY_SUPERVISION]}{RESET}" if s[KEY_SUPERVISION] > 0 else f"{s[KEY_SUPERVISION]}"
            missing_str = f"{YELLOW}{s['missing']}{RESET}" if s['missing'] > 0 else f"{s['missing']}"
            print(f"  {region:<12}{s['total']:>5}{s[GENERAL]:>6}{s[EXCEEDING]:>7}    {key_str}{'':<8}{missing_str}")

    if any_missing:
        print(f"\n{YELLOW}  缺项明细:{RESET}")
        for r in any_missing:
            items_str = "、".join(r.missing_items)
            print(f"    - {r.project_name} ({r.region}): 缺 {items_str}")

    print(f"{'='*60}\n")


def print_inspection_list(results: List[RiskResult]):
    high_risk = [r for r in results if r.level in (EXCEEDING, KEY_SUPERVISION)]
    if not high_risk:
        print(f"\n{DIM}当前筛选范围内无超过一定规模或重点督办项目，无需生成巡检清单。{RESET}\n")
        return

    print(f"\n{'='*60}")
    print(f"{BOLD}{RED}  巡检核查清单{RESET}")
    print(f"  共 {len(high_risk)} 个高风险项目")
    print(f"{'='*60}")

    for i, r in enumerate(high_risk, 1):
        icon = "★★★" if r.level == KEY_SUPERVISION else "▲"
        color = RED if r.level == KEY_SUPERVISION else YELLOW
        print(f"\n{BOLD}{i}. {r.project_name}{RESET}  {DIM}({r.region} / {r.hazard_type}){RESET}")
        print(f"   等级: {color}{icon} {r.level}{RESET}")

        if r.missing_items:
            items_str = "、".join(r.missing_items)
            print(f"   {RED}缺项: {items_str}{RESET}")

        if r.inspection_questions:
            print(f"   现场追问 ({len(r.inspection_questions)}条):")
            for j, q in enumerate(r.inspection_questions, 1):
                print(f"     {j}) {q}")
        else:
            print(f"   {DIM}(无可自动生成的追问项，请根据现场情况灵活核查){RESET}")

    print(f"\n{'='*60}\n")


def print_region_summary(results: List[RiskResult]):
    region_stats = _summarize_by_region(results)
    if not region_stats:
        print(f"\n{DIM}暂无数据。{RESET}\n")
        return

    print(f"\n{'='*60}")
    print(f"{BOLD}  区域风险汇总{RESET}")
    print(f"{'='*60}")
    print(f"  {'区域':<14}{'总数':>5}{'一般危大':>8}{'超规模':>7}{'重点督办':>8}{'缺项':>6}")
    print(f"  {'-'*52}")
    for region in sorted(region_stats.keys()):
        s = region_stats[region]
        key_str = f"{RED}{BOLD}{s[KEY_SUPERVISION]}{RESET}" if s[KEY_SUPERVISION] > 0 else f"{s[KEY_SUPERVISION]}"
        missing_str = f"{YELLOW}{s['missing']}{RESET}" if s['missing'] > 0 else f"{s['missing']}"
        print(f"  {region:<14}{s['total']:>5}{s[GENERAL]:>8}{s[EXCEEDING]:>7}    {key_str}{'':<10}{missing_str}")
    print(f"{'='*60}\n")


LEVEL_PRIORITY = {
    KEY_SUPERVISION: 0,
    EXCEEDING: 1,
    GENERAL: 2,
}


def sort_by_priority(results: List[RiskResult]) -> List[RiskResult]:
    return sorted(results, key=lambda r: (LEVEL_PRIORITY.get(r.level, 99), len(r.missing_items) * -1))


def group_by_region(results: List[RiskResult]) -> Dict[str, List[RiskResult]]:
    grouped = defaultdict(list)
    for r in results:
        grouped[r.region].append(r)
    for region in grouped:
        grouped[region] = sort_by_priority(grouped[region])
    return dict(grouped)


def print_weekly_report(results: List[RiskResult], top_per_region: int = 3):
    if not results:
        print(f"\n{DIM}未找到匹配的项目。{RESET}")
        return

    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")

    print(f"\n{'='*65}")
    print(f"{BOLD}  危大工程周报 - 重点项目清单{RESET}  {DIM}({today}){RESET}")
    print(f"{'='*65}")

    general_n = sum(1 for r in results if r.level == GENERAL)
    exceed_n = sum(1 for r in results if r.level == EXCEEDING)
    key_n = sum(1 for r in results if r.level == KEY_SUPERVISION)
    missing_n = sum(1 for r in results if r.missing_items)

    print(f"  项目总数: {len(results)} | 一般危大: {general_n} | "
          f"超规模: {exceed_n} | {RED}重点督办: {key_n}{RESET} | {YELLOW}缺项: {missing_n}{RESET}")

    grouped = group_by_region(results)

    for region in sorted(grouped.keys()):
        items = grouped[region]
        key_count = sum(1 for r in items if r.level == KEY_SUPERVISION)
        exceed_count = sum(1 for r in items if r.level == EXCEEDING)

        print(f"\n{BOLD}{CYAN}【{region}】{RESET}"
              f"  共{len(items)}项  "
              f"{RED}★重点{key_count}{RESET}  "
              f"{YELLOW}▲超规模{exceed_count}{RESET}")
        print(f"  {'-'*58}")

        top_items = items[:top_per_region]
        for i, r in enumerate(top_items, 1):
            icon = LEVEL_ICONS.get(r.level, "○")
            color = LEVEL_COLORS.get(r.level, "")
            missing_tag = f" {RED}[缺{len(r.missing_items)}项]{RESET}" if r.missing_items else ""
            print(f"  {i}. {color}{icon} {r.level}{RESET} - {BOLD}{r.project_name}{RESET}{missing_tag}")
            print(f"     类型: {r.hazard_type}")
            if r.key_reasons:
                print(f"     关注原因: {r.key_reasons[0]}")
            elif r.triggers:
                print(f"     主要触发: {r.triggers[0]}")
            if r.inspection_questions:
                print(f"     重点追问: {r.inspection_questions[0]}")

        if len(items) > top_per_region:
            rest = items[top_per_region:]
            rest_names = "、".join(r.project_name for r in rest[:3])
            more = len(rest) - 3 if len(rest) > 3 else 0
            suffix = f"等{len(rest)}项" if more > 0 else ""
            print(f"  {DIM}  其余: {rest_names}{suffix}{RESET}")

    all_key = [r for r in results if r.level == KEY_SUPERVISION]
    if all_key:
        print(f"\n{BOLD}{RED}  ★ 全集团重点督办项目 ({len(all_key)}项){RESET}")
        print(f"  {'-'*58}")
        for i, r in enumerate(sort_by_priority(all_key), 1):
            print(f"  {i}. {r.project_name} ({r.region}) - {r.hazard_type}")
            if r.key_reasons:
                reasons = "；".join(r.key_reasons[:2])
                print(f"     → {reasons}")

    print(f"\n{'='*65}\n")
