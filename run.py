import argparse
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def find_data_file(name_hint: str = None) -> str:
    candidates = []
    if os.path.isdir(DATA_DIR):
        for f in os.listdir(DATA_DIR):
            if f.endswith(".json"):
                candidates.append(os.path.join(DATA_DIR, f))

    if name_hint:
        matched = [c for c in candidates if name_hint in os.path.basename(c)]
        if matched:
            return matched[0]

    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        for c in candidates:
            print(f"  - {os.path.basename(c)}")
        return candidates[0]

    print(f"错误: data目录下未找到JSON项目清单文件。")
    print(f"请将项目清单JSON文件放入: {DATA_DIR}")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="危大工程方案风险评分工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py                          检查data目录下所有项目
  python run.py -n 朝阳                  筛选名称含"朝阳"的项目
  python run.py -r 华东区                筛选华东区项目
  python run.py -n 朝阳 -r 华东区        名称+区域组合筛选
  python run.py --list                   仅列出项目清单，不评分
  python run.py --inspect                输出巡检核查清单
        """,
    )
    parser.add_argument("-n", "--name", help="按项目名称筛选(模糊匹配)")
    parser.add_argument("-r", "--region", help="按区域筛选(模糊匹配)")
    parser.add_argument("-f", "--file", help="指定项目清单JSON文件路径")
    parser.add_argument("--list", action="store_true", help="仅列出项目清单")
    parser.add_argument("--inspect", action="store_true", help="输出巡检核查清单")

    args = parser.parse_args()

    filepath = args.file if args.file else find_data_file()
    if not os.path.isfile(filepath):
        print(f"错误: 文件不存在 - {filepath}")
        sys.exit(1)

    from risk_tool.loader import load_projects, filter_projects, evaluate
    from risk_tool.report import print_results, print_inspection_list

    projects = load_projects(filepath)

    if args.name or args.region:
        projects = filter_projects(projects, name=args.name, region=args.region)

    if args.list:
        print(f"\n项目清单 (共{len(projects)}个):")
        for i, p in enumerate(projects, 1):
            depth = f"开挖{p.excavation_depth}m" if p.excavation_depth else ""
            height = f"架高{p.scaffold_height}m" if p.scaffold_height else ""
            weight = f"吊装{p.lifting_weight}t" if p.lifting_weight else ""
            specs = " | ".join(filter(None, [depth, height, weight]))
            print(f"  {i}. {p.name} ({p.region}) - {p.hazard_type}  {specs}")
        print()
        return

    results = evaluate(projects)
    print_results(results)

    if args.inspect:
        print_inspection_list(results)
    elif any(r.level in ("超过一定规模危大", "重点督办") for r in results):
        from risk_tool.classifier import KEY_SUPERVISION
        has_key = any(r.level == KEY_SUPERVISION for r in results)
        if has_key:
            print(f"提示: 存在重点督办项目，可使用 --inspect 参数生成巡检核查清单。\n")


if __name__ == "__main__":
    main()
