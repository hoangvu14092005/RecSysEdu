"""Commands for data preparation, reproducible experiments and snapshots."""

import argparse
import json
import sys
from pathlib import Path

import yaml

from recsysedu.data.audit import audit_dataset
from recsysedu.data.download import fetch_sources
from recsysedu.demo.artifacts import load_bundle


def _config(path: str) -> dict:
    value = yaml.safe_load(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise ValueError('Config phải là object YAML')
    return value


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='RecSysEdu base: dữ liệu và demo snapshot')
    commands = parser.add_subparsers(dest='command', required=True)
    data = commands.add_parser('data', help='Tải và khảo sát raw MOOCCubeX')
    actions = data.add_subparsers(dest='action', required=True)
    for name in ('download', 'audit', 'prepare', 'split'):
        action = actions.add_parser(name)
        action.add_argument('--config', default=(
            f'configs/{name}.yaml' if name in ('prepare', 'split') else 'configs/data.yaml'))
        if name == 'audit':
            action.add_argument('--max-users', type=int, default=0, help='0: toàn bộ user')
            action.add_argument('--output', help='File báo cáo JSON tổng hợp')
    demo = commands.add_parser('demo', help='Kiểm định dạng snapshot cho UI')
    demo_actions = demo.add_subparsers(dest='action', required=True)
    validate = demo_actions.add_parser('validate')
    validate.add_argument('--bundle', default='tests/fixtures/demo_bundle.json')
    export = demo_actions.add_parser('export', help='Xuất snapshot từ run offline đã hoàn tất')
    export.add_argument('--run-dir', action='append', required=True,
                        help='Thư mục run; lặp lại cho từng model đã chọn')
    export.add_argument('--user-id', action='append', required=True,
                        help='ID hồ sơ trong cohort; lặp lại để chọn nhiều hồ sơ')
    export.add_argument('--output', required=True, help='File snapshot nằm ngoài batch kết quả')
    train = commands.add_parser('train', help='Huấn luyện BPR trên split đã phát hành')
    train.add_argument('--model', choices=('bpr',), required=True)
    train.add_argument('--config', default='configs/bpr.yaml')
    train.add_argument('--output', help='Thư mục model mới; không ghi đè')
    for name in ('evaluate', 'experiments'):
        command = commands.add_parser(name, help=(
            'Đánh giá một model' if name == 'evaluate' else 'Chạy bốn model cùng protocol'))
        if name == 'evaluate':
            command.add_argument('--model', choices=('popularity', 'content', 'bpr', 'hybrid'),
                                 required=True)
        command.add_argument('--split', choices=('valid', 'test'), required=True)
        command.add_argument('--config', default='configs/final_experiments.yaml')
        command.add_argument('--output', help='Root kết quả; mỗi lần chạy tạo batch mới')
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            if args.action == 'export':
                from recsysedu.demo.export import export_demo_bundle

                bundle = export_demo_bundle([Path(path) for path in args.run_dir],
                                            args.user_id, Path(args.output))
                print(f"Đã xuất snapshot offline: {len(bundle['users'])} hồ sơ, "
                      f"{len(bundle['runs'])} model; dataset: {bundle['meta']['dataset_version']}; "
                      f"file: {Path(args.output).resolve()}")
                return 0
            bundle = load_bundle(Path(args.bundle))
            print(f"Snapshot hợp lệ: {bundle['meta']['data_mode']}, "
                  f"{len(bundle['users'])} hồ sơ; không phải kết quả train thật nếu synthetic.")
            return 0
        config = _config(args.config)
        if args.command == 'train':
            from recsysedu.experiments.runner import train_from_config

            report = train_from_config(Path(args.config),
                                       output_dir=Path(args.output) if args.output else None)
            print(f"BPR đã train {report['epochs_completed']} epoch; "
                  f"manifest: {report['manifest_path']}; chưa phải kết quả đánh giá chất lượng.")
            return 0
        if args.command in ('evaluate', 'experiments'):
            from recsysedu.experiments.runner import evaluate_model, run_experiment

            base = Path(args.config).resolve().parent
            config['_base_dir'] = str(base)
            roots = config.get('output_roots', {})
            if not isinstance(roots, dict):
                raise ValueError('output_roots phải là object valid/test')
            root = roots.get(args.split, f'../results/{args.split}')
            if not isinstance(root, str) or not root.strip():
                raise ValueError('output root phải là đường dẫn string không rỗng')
            output = Path(args.output) if args.output else base / root
            if args.command == 'evaluate':
                reports = [evaluate_model(config, model_id=args.model, split=args.split,
                                          output_root=output)]
            else:
                reports = run_experiment(config, split=args.split, output_root=output)
            for report in reports:
                print(f"{report['model_id']}: {report['run_id']}; "
                      f"NDCG@10={report['metrics']['NDCG@10']:.6f}; split={args.split}")
            print(f'Kết quả: {output.resolve()}')
            return 0
        if args.action == 'download':
            fetch_sources(config)
        elif args.action == 'prepare':
            from recsysedu.data.prepare import prepare_dataset

            required = ('raw_dir', 'output_dir', 'dataset_version', 'time_basis',
                        'sample_users', 'seed')
            missing = [key for key in required if key not in config]
            if missing:
                raise ValueError(f"Config thiếu trường: {', '.join(missing)}")
            for key in ('raw_dir', 'output_dir'):
                if not isinstance(config[key], str) or not config[key].strip():
                    raise ValueError(f'{key} phải là đường dẫn string không rỗng')
            raw = Path(config['raw_dir'])
            output = Path(config['output_dir'])
            report = prepare_dataset(raw / 'course.json', raw / 'user.json', output,
                                     **{key: config[key] for key in required[2:]})
            print(f"Dataset {report['dataset_version']}: {report['selected_user_count']} user; "
                  f"output: {output}")
        elif args.action == 'split':
            from recsysedu.data.split import build_temporal_split

            required = ('prepared_dir', 'output_dir', 'split_version', 'seed')
            missing = [key for key in required if key not in config]
            if missing:
                raise ValueError(f"Config thiếu trường: {', '.join(missing)}")
            for key in ('prepared_dir', 'output_dir'):
                if not isinstance(config[key], str) or not config[key].strip():
                    raise ValueError(f'{key} phải là đường dẫn string không rỗng')
            prepared = Path(config['prepared_dir'])
            output = Path(config['output_dir'])
            report = build_temporal_split(
                prepared / 'interactions.parquet', prepared / 'courses.parquet', output,
                split_version=config['split_version'], seed=config['seed'])
            sizes = report['warm_cohort_sizes']
            print(f"Split {report['split_version']}: warm valid={sizes['valid']}, "
                  f"test={sizes['test']}; output: {output}")
        else:
            raw = Path(config['raw_dir'])
            report = audit_dataset(raw / 'course.json', raw / 'user.json',
                                   max_users=args.max_users)
            output = Path(args.output or config['audit_output'])
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f"Audit {report['scope']}: {report['users_scanned']} user, "
                  f"{report['unique_course_ids']} course; báo cáo: {output}")
            print(f"Timezone: {report['timezone_status']}; chưa phát hành temporal split.")
        return 0
    except (OSError, ValueError, KeyError, yaml.YAMLError) as exc:
        print(f'Lỗi: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
