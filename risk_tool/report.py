from typing import List
from risk_tool.models import RiskResult
from risk_tool.classifier import KEY_SUPERVISION, EXCEEDING


LEVEL_ICONS = {
    "一般危大": "●",
    "超过一定规模危大": "▲",
    "重点督办": "★★★",
}

LEVEL_COLORS = {
    "一般危大": "\033[92m",
    "超过一定规模危大": "\033[93m",
    "重点督办": "\033[91m",
}

RESET = "\033[0m"
BOLD = "\033[1m"
CYAN = "\033[96m"
DIM = "\033[2m"
RED = "\033[91m"
YELLOW = "\033[93m"


def print_results(results: List[RiskResult], verbose: bool = True):
    if not results:
        print(f"\n{DIM}未找到匹配的项目。{RESET}")
        return

    print(f"\n{'='*60}")
    print(f"{BOLD}  危大工程方案风险评分报告{RESET}")
    print(f"{'='*60}")

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

    general = [r for r in results if r.level == "一般危大"]
    exceeding = [r for r in results if r.level == "超过一定规模危大"]
    key = [r for r in results if r.level == KEY_SUPERVISION]

    print(f"  统计: 共{len(results)}个项目")
    print(f"    一般危大:       {len(general)}个")
    print(f"    超过一定规模:   {len(exceeding)}个")
    print(f"    重点督办:       {RED}{BOLD}{len(key)}个{RESET}")

    any_missing = [r for r in results if r.missing_items]
    if any_missing:
        print(f"\n  {YELLOW}存在缺项的项目: {len(any_missing)}个{RESET}")
        for r in any_missing:
            items_str = "、".join(r.missing_items)
            print(f"    - {r.project_name}: 缺 {items_str}")

    print(f"{'='*60}\n")


def print_inspection_list(results: List[RiskResult]):
    high_risk = [r for r in results if r.level in (EXCEEDING, KEY_SUPERVISION)]
    if not high_risk:
        print(f"\n{DIM}当前筛选范围内无超过一定规模或重点督办项目，无需生成巡检清单。{RESET}\n")
        return

    print(f"\n{'='*60}")
    print(f"{BOLD}{RED}  巡检核查清单{RESET}")
    print(f"{'='*60}")

    for i, r in enumerate(high_risk, 1):
        icon = "★★★" if r.level == KEY_SUPERVISION else "▲"
        print(f"\n{BOLD}{i}. {r.project_name}{RESET}  {DIM}({r.region} / {r.hazard_type}){RESET}")
        print(f"   等级: {icon} {r.level}")

        if r.missing_items:
            items_str = "、".join(r.missing_items)
            print(f"   {RED}缺项: {items_str}{RESET}")

        if r.inspection_questions:
            print(f"   现场追问:")
            for j, q in enumerate(r.inspection_questions, 1):
                print(f"     {j}) {q}")
        else:
            print(f"   {DIM}(无可自动生成的追问项，请根据现场情况灵活核查){RESET}")

    print(f"\n{'='*60}\n")
