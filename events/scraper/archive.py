import json
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DIR = BASE_DIR / 'raw'


def new_run_id():
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def save_raw_run(run_id, source, data):
    run_dir = RAW_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    filepath = run_dir / f'{source}.json'
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    return filepath


def load_raw(run_id, source):
    filepath = RAW_DIR / run_id / f'{source}.json'
    if not filepath.exists():
        raise FileNotFoundError(f'No raw data for {source} in run {run_id}')
    with open(filepath) as f:
        return json.load(f)


def load_latest_raw(source):
    run_ids = sorted([d.name for d in RAW_DIR.iterdir() if d.is_dir()], reverse=True)
    for rid in run_ids:
        filepath = RAW_DIR / rid / f'{source}.json'
        if filepath.exists():
            return rid, load_raw(rid, source)
    raise FileNotFoundError(f'No raw data found for {source}')


def list_runs():
    if not RAW_DIR.exists():
        return []
    return sorted([d.name for d in RAW_DIR.iterdir() if d.is_dir()])


def write_manifest(run_id, source_counts, mode='offline'):
    manifest = {
        'run_id': run_id,
        'created_at': datetime.now().isoformat(),
        'source_counts': source_counts,
        'mode': mode,
    }
    run_dir = RAW_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    with open(run_dir / 'manifest.json', 'w') as f:
        json.dump(manifest, f, indent=2)
    return manifest


def purge_old_runs(keep=20):
    run_ids = list_runs()
    if len(run_ids) <= keep:
        return 0
    to_remove = run_ids[:-keep]
    for rid in to_remove:
        shutil.rmtree(RAW_DIR / rid)
    return len(to_remove)
