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
示例:
  python run.py                          扫描data目录所有JSON，合并评分
  python run.py -n 朝阳                  筛选名称含"朝阳"的项目
  python run.py -r 华东区                筛选华东区项目
  python run.py -n 朝阳 -r 华东区        名称+区域组合筛选
  python run.py -f path/to/file.json     指定单个项目清单文件
  python run.py --list                   仅列出项目清单
  python run.py --inspect                输出巡检核查清单
  python run.py --region-summary         仅输出区域汇总(快速看周报)
  python run.py --export md              导出Markdown报告
  python run.py --export csv             导出CSV表格(评分+巡检两份)
  python run.py --export all             同时导出Markdown和CSV
  python run.py -c custom_config.json    使用自定义配置文件
        """,
    )
    parser.add_argument("-n", "--name", help="按项目名称筛选(模糊匹配)")
    parser.add_argument("-r", "--region", help="按区域筛选(模糊匹配)")
    parser.add_argument("-f", "--file", help="指定单个项目清单JSON文件路径")
    parser.add_argument("-d", "--dir", help=f"指定项目清单目录(默认: data/)")
    parser.add_argument("-c", "--config", help=f"指定配置文件路径(默认: config.json)")
    parser.add_argument("--list", action="store_true", help="仅列出项目清单，不评分")
    parser.add_argument("--inspect", action="store_true", help="输出巡检核查清单")
    parser.add_argument("--region-summary", action="store_true", help="仅输出区域汇总(快速周报模式)")
    parser.add_argument("--export", choices=["md", "markdown", "csv", "all"], help="导出报告格式")
    parser.add_argument("-o", "--output-dir", help=f"导出目录(默认: output/)")

    args = parser.parse_args()

    from risk_tool.loader import filter_projects, evaluate
    from risk_tool.classifier import load_config
    from risk_tool.report import print_results, print_inspection_list, print_region_summary

    config_path = args.config if args.config else DEFAULT_CONFIG
    if not os.path.isfile(config_path):
        print(f"错误: 配置文件不存在 - {config_path}")
        sys.exit(1)
    config = load_config(config_path)

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

    print_results(results)

    if args.inspect:
        print_inspection_list(results)

    if args.export:
        from risk_tool.exporter import export as export_results
        out_dir = args.output_dir if args.output_dir else OUTPUT_DIR
        exported = export_results(results, fmt=args.export, output_dir=out_dir)
        print(f"\n导出完成 ({len(exported)}个文件):")
        for f in exported:
            print(f"  → {f}")
        print()

    if not args.inspect and not args.export:
        from risk_tool.classifier import KEY_SUPERVISION
        has_key = any(r.level == KEY_SUPERVISION for r in results)
        if has_key:
            print(f"提示: 存在重点督办项目，可用 --inspect 查看巡检清单、--export 导出报告。\n")


if __name__ == "__main__":
    main()
