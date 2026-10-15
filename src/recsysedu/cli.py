"""Commands for raw data, versioned preparation and snapshot validation."""

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
    for name in ('download', 'audit', 'prepare'):
        action = actions.add_parser(name)
        action.add_argument('--config', default=(
            'configs/prepare.yaml' if name == 'prepare' else 'configs/data.yaml'))
        if name == 'audit':
            action.add_argument('--max-users', type=int, default=0, help='0: toàn bộ user')
            action.add_argument('--output', help='File báo cáo JSON tổng hợp')
    demo = commands.add_parser('demo', help='Kiểm định dạng snapshot cho UI')
    demo_actions = demo.add_subparsers(dest='action', required=True)
    validate = demo_actions.add_parser('validate')
    validate.add_argument('--bundle', default='tests/fixtures/demo_bundle.json')
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            bundle = load_bundle(Path(args.bundle))
            print(f"Snapshot hợp lệ: {bundle['meta']['data_mode']}, "
                  f"{len(bundle['users'])} hồ sơ; không phải kết quả train thật nếu synthetic.")
            return 0
        config = _config(args.config)
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
