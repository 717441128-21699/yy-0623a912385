import argparse
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
DEFAULT_CONFIG = os.path.join(BASE_DIR, "config.json")


def load_all_projects(filepath: str = None, dirpath: str = None):
    from risk_tool.loader import load_projects, load_projects_from_dir, find_json_files

    if filepath:
        if os.path.isfile(filepath):
            return load_projects(filepath), [filepath]
        print(f"错误: 文件不存在 - {filepath}")
        sys.exit(1)

    if dirpath and os.path.isdir(dirpath):
        files = find_json_files(dirpath)
        if not files:
            print(f"错误: {dirpath} 目录下未找到JSON项目清单文件。")
            sys.exit(1)
        return load_projects_from_dir(dirpath), files

    if os.path.isdir(DATA_DIR):
        files = find_json_files(DATA_DIR)
        if files:
            return load_projects_from_dir(DATA_DIR), files

    print(f"错误: 未找到项目清单文件。")
    print(f"请将JSON项目清单放入 data/ 目录，或使用 -f 参数指定文件。")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="危大工程方案风险评分工具 - 周报前快速筛选重点项目",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
常用场景:
  python run.py                          扫描data目录所有JSON，合并评分
  python run.py --weekly                 周报模式：按区域分组、按风险排序
  python run.py -r 华东区 --weekly       单区域周报
  python run.py --export weekly          导出周报Markdown
  python run.py --compare --prev data/上周/ --curr data/本周/   批次对比
  python run.py --compare -f 本周.json --prev 上周.json        两文件对比

筛选与输出:
  -n 朝阳 -r 华东区                      按名称/区域筛选
  --list / --inspect / --region-summary  不同展示模式
  --export md|csv|weekly|all             导出报告
  -c custom_config.json                  自定义配置
        """,
    )
    parser.add_argument("-n", "--name", help="按项目名称筛选(模糊匹配)")
    parser.add_argument("-r", "--region", help="按区域筛选(模糊匹配)")
    parser.add_argument("-f", "--file", help="指定单个项目清单JSON文件路径")
    parser.add_argument("-d", "--dir", help=f"指定项目清单目录(默认: data/)")
    parser.add_argument("-c", "--config", help=f"指定配置文件路径(默认: config.json)")
    parser.add_argument("-o", "--output-dir", help=f"导出目录(默认: output/)")

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--list", action="store_true", help="仅列出项目清单")
    mode_group.add_argument("--region-summary", action="store_true", help="仅输出区域汇总")
    mode_group.add_argument("--weekly", action="store_true", help="周报模式：按区域分组+按风险排序")

    parser.add_argument("--inspect", action="store_true", help="输出巡检核查清单")
    parser.add_argument("--export", choices=["md", "markdown", "csv", "weekly", "all"], help="导出报告格式")

    compare_group = parser.add_argument_group("批次对比")
    compare_group.add_argument("--compare", action="store_true", help="启用批次对比模式")
    compare_group.add_argument("--prev", help="对比基准(上周)文件或目录路径")
    compare_group.add_argument("--curr", help="对比对象(本周)文件或目录路径；-f 指定的视为本周")
    compare_group.add_argument("--prev-label", default="上周", help="基准批次标签(默认: 上周)")
    compare_group.add_argument("--curr-label", default="本周", help="当前批次标签(默认: 本周)")

    args = parser.parse_args()

    from risk_tool.loader import filter_projects, evaluate
    from risk_tool.classifier import load_config
    from risk_tool.report import (
        print_results, print_inspection_list, print_region_summary,
        print_weekly_report,
    )

    config_path = args.config if args.config else DEFAULT_CONFIG
    if not os.path.isfile(config_path):
        print(f"错误: 配置文件不存在 - {config_path}")
        sys.exit(1)
    config = load_config(config_path)
    top_per_region = config.get("weekly_report", {}).get("top_per_region", 3)

    if args.compare:
        _do_compare(args, config, top_per_region)
        return

    projects, files_used = load_all_projects(filepath=args.file, dirpath=args.dir)

    if args.name or args.region:
        projects = filter_projects(projects, name=args.name, region=args.region)

    if args.list:
        print(f"\n项目清单 (共{len(projects)}个，来自{len(files_used)}个文件):")
        for f in files_used:
            print(f"  文件: {os.path.basename(f)}")
        print()
        for i, p in enumerate(projects, 1):
            depth = f"开挖{p.excavation_depth}m" if p.excavation_depth else ""
            height = f"架高{p.scaffold_height}m" if p.scaffold_height else ""
            weight = f"吊装{p.lifting_weight}t" if p.lifting_weight else ""
            specs = " | ".join(filter(None, [depth, height, weight]))
            print(f"  {i}. {p.name} ({p.region}) - {p.hazard_type}  {specs}")
        print()
        return

    results = evaluate(projects, config)

    if args.region_summary:
        print_region_summary(results)
        return

    if args.weekly:
        print_weekly_report(results, top_per_region=top_per_region)
    else:
        print_results(results)

    if args.inspect:
        print_inspection_list(results)

    if args.export:
        from risk_tool.exporter import export as export_results
        out_dir = args.output_dir if args.output_dir else OUTPUT_DIR
        exported = export_results(
            results, fmt=args.export, output_dir=out_dir,
            top_per_region=top_per_region,
        )
        print(f"\n导出完成 ({len(exported)}个文件):")
        for f in exported:
            print(f"  → {f}")
        print()

    if not args.inspect and not args.export and not args.weekly:
        from risk_tool.classifier import KEY_SUPERVISION
        has_key = any(r.level == KEY_SUPERVISION for r in results)
        if has_key:
            print(f"提示: 存在重点督办项目，可用 --weekly 看周报、--inspect 看巡检清单、--export 导出。\n")


def _do_compare(args, config, top_per_region):
    from risk_tool.loader import load_projects, load_projects_from_dir, filter_projects, evaluate, find_json_files
    from risk_tool.comparator import compare_results, print_comparison, export_comparison_markdown, export_comparison_csv

    prev_path = args.prev
    curr_path = args.curr if args.curr else args.file

    if not prev_path:
        print("错误: 对比模式下必须指定 --prev <上周文件或目录>")
        sys.exit(1)

    if os.path.isfile(prev_path):
        prev_projects = load_projects(prev_path)
    elif os.path.isdir(prev_path):
        prev_projects = load_projects_from_dir(prev_path)
    else:
        print(f"错误: 基准文件/目录不存在 - {prev_path}")
        sys.exit(1)

    if curr_path and os.path.isfile(curr_path):
        curr_projects = load_projects(curr_path)
    elif curr_path and os.path.isdir(curr_path):
        curr_projects = load_projects_from_dir(curr_path)
    elif not curr_path:
        curr_projects, _ = load_all_projects()
    else:
        print(f"错误: 对比文件/目录不存在 - {curr_path}")
        sys.exit(1)

    if args.name or args.region:
        prev_projects = filter_projects(prev_projects, name=args.name, region=args.region)
        curr_projects = filter_projects(curr_projects, name=args.name, region=args.region)

    prev_results = evaluate(prev_projects, config)
    curr_results = evaluate(curr_projects, config)

    comparisons = compare_results(curr_results, prev_results)

    print_comparison(comparisons)

    if args.export:
        out_dir = args.output_dir if args.output_dir else OUTPUT_DIR
        exported = []
        if args.export in ("md", "markdown", "all"):
            exported.append(export_comparison_markdown(
                comparisons, out_dir,
                curr_label=args.curr_label, prev_label=args.prev_label,
            ))
        if args.export in ("csv", "all"):
            exported.append(export_comparison_csv(
                comparisons, out_dir,
                curr_label=args.curr_label, prev_label=args.prev_label,
            ))
        if exported:
            print(f"对比报告导出完成 ({len(exported)}个文件):")
            for f in exported:
                print(f"  → {f}")
            print()

    if not args.export:
        print(f"提示: 可用 --export md 或 --export csv 导出对比报告。\n")


if __name__ == "__main__":
    main()
