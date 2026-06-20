import csv
import os
from datetime import datetime
from typing import List, Dict, Tuple
from collections import defaultdict
from risk_tool.models import RiskResult
from risk_tool.classifier import KEY_SUPERVISION, EXCEEDING, GENERAL


LEVEL_PRIORITY = {
    KEY_SUPERVISION: 0,
    EXCEEDING: 1,
    GENERAL: 2,
}


class CompareResult:
    def __init__(self, curr: RiskResult = None, prev: RiskResult = None):
        self.current = curr
        self.previous = prev
        self.status = "unchanged"
        self.level_up = False
        self.level_down = False
        self.new_project = False
        self.removed = False
        self.new_key_supervision = False
        self.downgraded_from_key = False
        self.unfixed_missing = []
        self.new_missing = []
        self.fixed_missing = []
        self._analyze()

    def _analyze(self):
        if self.current and not self.previous:
            self.new_project = True
            self.status = "new"
            if self.current.level == KEY_SUPERVISION:
                self.new_key_supervision = True
            return

        if self.previous and not self.current:
            self.removed = True
            self.status = "removed"
            return

        curr_pri = LEVEL_PRIORITY.get(self.current.level, 99)
        prev_pri = LEVEL_PRIORITY.get(self.previous.level, 99)

        if curr_pri < prev_pri:
            self.level_up = True
            self.status = "upgraded"
            if self.current.level == KEY_SUPERVISION:
                self.new_key_supervision = True
        elif curr_pri > prev_pri:
            self.level_down = True
            self.status = "downgraded"
            if self.previous.level == KEY_SUPERVISION:
                self.downgraded_from_key = True
        else:
            self.status = "unchanged"

        prev_missing = set(self.previous.missing_items)
        curr_missing = set(self.current.missing_items)

        self.unfixed_missing = sorted(prev_missing & curr_missing)
        self.new_missing = sorted(curr_missing - prev_missing)
        self.fixed_missing = sorted(prev_missing - curr_missing)


def compare_results(current: List[RiskResult], previous: List[RiskResult]) -> Dict[str, CompareResult]:
    prev_map = {r.project_name: r for r in previous}
    curr_map = {r.project_name: r for r in current}

    results = {}
    all_names = set(curr_map.keys()) | set(prev_map.keys())

    for name in all_names:
        cr = curr_map.get(name)
        pr = prev_map.get(name)
        results[name] = CompareResult(cr, pr)

    return results


def print_comparison(comparisons: Dict[str, CompareResult]):
    if not comparisons:
        print("\n  暂无对比数据。\n")
        return

    new_keys = [c for c in comparisons.values() if c.new_key_supervision and not c.new_project]
    new_project_keys = [c for c in comparisons.values() if c.new_project and c.current and c.current.level == KEY_SUPERVISION]
    downgraded = [c for c in comparisons.values() if c.level_down]
    unfixed = [c for c in comparisons.values() if c.unfixed_missing and c.current]
    new_projects = [c for c in comparisons.values() if c.new_project]
    removed = [c for c in comparisons.values() if c.removed]
    fixed_missing = [c for c in comparisons.values() if c.fixed_missing and c.current]

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    print(f"\n{'='*65}")
    print(f"{BOLD}  危大工程批次对比报告{RESET}")
    print(f"{'='*65}")
    print(f"  项目总数: {len(comparisons)} | "
          f"{RED}新增重点督办: {len(new_keys) + len(new_project_keys)}{RESET} | "
          f"{GREEN}降级: {len(downgraded)}{RESET} | "
          f"{YELLOW}缺项未整改: {len(unfixed)}{RESET}")
    print(f"  新增项目: {len(new_projects)} | 移出项目: {len(removed)} | 已整改缺项: {len(fixed_missing)}")

    if new_keys or new_project_keys:
        all_new_key = new_keys + new_project_keys
        print(f"\n{RED}{BOLD}  新增重点督办项目 ({len(all_new_key)}项){RESET}")
        print(f"  {'-'*58}")
        for i, c in enumerate(sorted(all_new_key, key=lambda x: x.current.project_name), 1):
            r = c.current
            tag = "[新录入]" if c.new_project else ""
            print(f"  {i}. {BOLD}{r.project_name}{RESET} {DIM}({r.region}){RESET} {YELLOW}{tag}{RESET}")
            print(f"     类型: {r.hazard_type}")
            if c.previous:
                print(f"     变化: {c.previous.level} → {r.level}")
            if r.key_reasons:
                for reason in r.key_reasons[:2]:
                    print(f"     → {reason}")

    if downgraded:
        print(f"\n{GREEN}{BOLD}  风险降级项目 ({len(downgraded)}项){RESET}")
        print(f"  {'-'*58}")
        for i, c in enumerate(sorted(downgraded, key=lambda x: x.current.project_name), 1):
            r = c.current
            print(f"  {i}. {BOLD}{r.project_name}{RESET} {DIM}({r.region}){RESET}")
            print(f"     变化: {c.previous.level} → {r.level}")
            if c.fixed_missing:
                print(f"     已整改缺项: {', '.join(c.fixed_missing)}")

    if unfixed:
        print(f"\n{YELLOW}{BOLD}  缺项仍未整改 ({len(unfixed)}项){RESET}")
        print(f"  {'-'*58}")
        for i, c in enumerate(sorted(unfixed, key=lambda x: -len(x.unfixed_missing)), 1):
            r = c.current
            print(f"  {i}. {BOLD}{r.project_name}{RESET} {DIM}({r.region}){RESET}")
            print(f"     连续缺项: {RED}{', '.join(c.unfixed_missing)}{RESET}")
            if c.new_missing:
                print(f"     新增缺项: {', '.join(c.new_missing)}")

    if new_projects and not new_project_keys:
        print(f"\n{CYAN}  新增项目 ({len(new_projects)}项){RESET}")
        for c in sorted(new_projects, key=lambda x: x.current.project_name):
            r = c.current
            print(f"    - {r.project_name} ({r.region}) - {r.level}")

    if removed:
        print(f"\n{DIM}  移出项目 ({len(removed)}项){RESET}")
        for c in sorted(removed, key=lambda x: x.previous.project_name):
            r = c.previous
            print(f"    - {r.project_name} ({r.region}) - {r.level}")

    print(f"\n{'='*65}\n")


def export_comparison_markdown(comparisons: Dict[str, CompareResult], output_dir: str = None,
                                curr_label: str = "本周", prev_label: str = "上周") -> str:
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(output_dir, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    fname = f"批次对比报告_{today}.md"
    fpath = os.path.join(output_dir, fname)

    new_keys = [c for c in comparisons.values() if c.new_key_supervision and not c.new_project]
    new_project_keys = [c for c in comparisons.values() if c.new_project and c.current and c.current.level == KEY_SUPERVISION]
    all_new_key = new_keys + new_project_keys
    downgraded = [c for c in comparisons.values() if c.level_down]
    unfixed = [c for c in comparisons.values() if c.unfixed_missing and c.current]
    new_projects = [c for c in comparisons.values() if c.new_project]
    removed = [c for c in comparisons.values() if c.removed]
    fixed = [c for c in comparisons.values() if c.fixed_missing and c.current]

    lines = []
    lines.append(f"# 危大工程批次对比报告")
    lines.append("")
    lines.append(f"> 生成日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"> 对比: {prev_label} → {curr_label}")
    lines.append(f"> 项目总数: {len(comparisons)} 个")
    lines.append("")

    lines.append("| 指标 | 数量 |")
    lines.append("|------|-----:|")
    lines.append(f"| 新增重点督办 | **{len(all_new_key)}** |")
    lines.append(f"| 风险降级 | {len(downgraded)} |")
    lines.append(f"| 缺项未整改 | {len(unfixed)} |")
    lines.append(f"| 缺项已整改 | {len(fixed)} |")
    lines.append(f"| 新增项目 | {len(new_projects)} |")
    lines.append(f"| 移出项目 | {len(removed)} |")
    lines.append("")

    if all_new_key:
        lines.append("## 新增重点督办项目")
        lines.append("")
        lines.append("| 项目 | 区域 | 类型 | 原等级 | 现等级 | 重点原因 |")
        lines.append("|------|------|------|--------|--------|----------|")
        for c in sorted(all_new_key, key=lambda x: x.current.project_name):
            r = c.current
            prev_level = c.previous.level if c.previous else "新项目"
            reasons = "；".join(r.key_reasons[:2]) if r.key_reasons else "-"
            lines.append(f"| **{r.project_name}** | {r.region} | {r.hazard_type} | {prev_level} | **{r.level}** | {reasons} |")
        lines.append("")

    if downgraded:
        lines.append("## 风险降级项目")
        lines.append("")
        lines.append("| 项目 | 区域 | 原等级 | 现等级 | 已整改缺项 |")
        lines.append("|------|------|--------|--------|------------|")
        for c in sorted(downgraded, key=lambda x: x.current.project_name):
            r = c.current
            fixed_str = "、".join(c.fixed_missing) if c.fixed_missing else "-"
            lines.append(f"| {r.project_name} | {r.region} | {c.previous.level} | {r.level} | {fixed_str} |")
        lines.append("")

    if unfixed:
        lines.append("## 缺项仍未整改")
        lines.append("")
        lines.append("| 项目 | 区域 | 等级 | 连续缺项 | 新增缺项 |")
        lines.append("|------|------|------|----------|----------|")
        for c in sorted(unfixed, key=lambda x: -len(x.unfixed_missing)):
            r = c.current
            unfix_str = "、".join(c.unfixed_missing)
            new_str = "、".join(c.new_missing) if c.new_missing else "-"
            lines.append(f"| {r.project_name} | {r.region} | {r.level} | {unfix_str} | {new_str} |")
        lines.append("")

    if new_projects:
        lines.append("## 新增项目")
        lines.append("")
        lines.append("| 项目 | 区域 | 类型 | 等级 |")
        lines.append("|------|------|------|------|")
        for c in sorted(new_projects, key=lambda x: x.current.project_name):
            r = c.current
            lines.append(f"| {r.project_name} | {r.region} | {r.hazard_type} | {r.level} |")
        lines.append("")

    if removed:
        lines.append("## 移出项目")
        lines.append("")
        lines.append("| 项目 | 区域 | 类型 | 原等级 |")
        lines.append("|------|------|------|--------|")
        for c in sorted(removed, key=lambda x: x.previous.project_name):
            r = c.previous
            lines.append(f"| {r.project_name} | {r.region} | {r.hazard_type} | {r.level} |")
        lines.append("")

    with open(fpath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return fpath


def export_comparison_csv(comparisons: Dict[str, CompareResult], output_dir: str = None,
                           curr_label: str = "本周", prev_label: str = "上周") -> str:
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(output_dir, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    fname = f"批次对比报告_{today}.csv"
    fpath = os.path.join(output_dir, fname)

    headers = [
        "项目名称", "区域", "工程类型",
        f"{prev_label}等级", f"{curr_label}等级",
        "变化状态", "是否新增重点督办", "是否降级",
        "连续未整改缺项", "新增缺项", "已整改缺项",
        "重点督办原因",
    ]

    with open(fpath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for name in sorted(comparisons.keys()):
            c = comparisons[name]
            r = c.current or c.previous
            prev_level = c.previous.level if c.previous else ""
            curr_level = c.current.level if c.current else ""
            status_map = {
                "new": "新增",
                "removed": "移出",
                "upgraded": "升级",
                "downgraded": "降级",
                "unchanged": "未变",
            }
            status = status_map.get(c.status, c.status)
            writer.writerow([
                r.project_name,
                r.region,
                r.hazard_type,
                prev_level,
                curr_level,
                status,
                "是" if c.new_key_supervision else "否",
                "是" if c.level_down else "否",
                "、".join(c.unfixed_missing),
                "、".join(c.new_missing),
                "、".join(c.fixed_missing),
                "；".join(r.key_reasons) if r.is_key_supervision else "",
            ])

    return fpath
