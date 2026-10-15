"""Download only requested source files, publishing after a complete transfer."""

import hashlib
import json
import time
from datetime import datetime, timezone
from http.client import IncompleteRead
from pathlib import Path
from urllib.request import Request, urlopen


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(url: str, destination: Path, *, timeout: int = 120, progress=None) -> dict:
    """Keep an existing file intact; incomplete transfers remain a .part file.

    SHA-256 identifies the received file, not an upstream-verified checksum.
    A retry restarts this file; HTTP resume is intentionally not implemented.
    """
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(f'File đã tồn tại: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + '.part')
    started = time.monotonic()
    digest = hashlib.sha256()
    count = 0
    request = Request(url, headers={'User-Agent': 'RecSysEdu/0.1'})
    try:
        with urlopen(request, timeout=timeout) as response, partial.open('wb') as output:
            if response.status != 200:
                raise ValueError(f'Không nhận được file đầy đủ: HTTP {response.status}')
            length = response.headers.get('Content-Length')
            expected = int(length) if length is not None else None
            first = True
            while chunk := response.read(1024 * 1024):
                if first:
                    prefix = chunk.removeprefix(b'\xef\xbb\xbf').lstrip()
                    if prefix[:1] not in (b'{', b'['):
                        raise ValueError('Nguồn không bắt đầu bằng dữ liệu JSON')
                    first = False
                output.write(chunk)
                digest.update(chunk)
                count += len(chunk)
                if progress:
                    progress(count, expected)
            if count == 0 or (expected is not None and count != expected):
                raise ValueError(f'Tải thiếu dữ liệu: {count}/{expected} bytes')
    except IncompleteRead as exc:
        raise ValueError('Kết nối kết thúc trước khi tải đủ dữ liệu') from exc
    partial.replace(destination)
    return {
        'name': destination.name,
        'url': url,
        'bytes': count,
        'sha256': digest.hexdigest(),
        'downloaded_at': datetime.now(timezone.utc).isoformat(),
        'elapsed_seconds': round(time.monotonic() - started, 2),
        'status': 'complete',
    }


def fetch_sources(config: dict) -> dict:
    """Download sequentially and persist provenance after each completed file."""
    raw_dir = Path(config['raw_dir'])
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = raw_dir / 'raw_manifest.json'
    manifest = (
        json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest_path.exists()
        else {'schema_version': 1, 'files': []}
    )
    records = {item['name']: item for item in manifest['files']}
    for name in config['files']:
        if Path(name).name != name or not name.endswith('.json'):
            raise ValueError(f'Tên file không hợp lệ: {name}')
        destination = raw_dir / name
        url = config['source_base'].rstrip('/') + '/' + name
        if destination.exists():
            record = records.get(name)
            if not record or record['url'] != url or file_sha256(destination) != record['sha256']:
                raise ValueError(f'File có sẵn không khớp manifest: {name}; không ghi đè')
            print(f'Đã kiểm checksum, giữ file: {name}', flush=True)
            continue
        last_report = -1

        def progress(count, total):
            nonlocal last_report
            bucket = count // (20 * 1024 * 1024)
            if bucket != last_report:
                last_report = bucket
                print(f'{name}: {count / 1048576:.1f} MiB / '
                      f'{total / 1048576:.1f} MiB' if total else f'{name}: {count} bytes',
                      flush=True)

        print(f'Bắt đầu tải: {name}', flush=True)
        records[name] = download_file(url, destination, progress=progress)
        manifest['files'] = list(records.values())
        temporary = manifest_path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(manifest_path)
        print(f'Đã tải và ghi SHA-256: {name}', flush=True)
    return manifest
