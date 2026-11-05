#!/usr/bin/env python3
"""Install only into this skill's runtime; download official CPU models explicitly.

模型默认从 hf-mirror 拉取（GitHub 在部分网络下不可达），失败再回退 huggingface.co。
"""
import argparse, hashlib, json, subprocess, sys, time, urllib.error, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime'
HOSTS = ['https://hf-mirror.com', 'https://huggingface.co']
MODELS = {
    'speech': {
        'dir': 'sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17',
        'repo': 'csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17',
        'files': ['model.int8.onnx', 'tokens.txt'],
    },
    'events': {
        'dir': 'sherpa-onnx-zipformer-small-audio-tagging-2024-04-15',
        'repo': 'k2-fsa/sherpa-onnx-zipformer-small-audio-tagging-2024-04-15',
        'files': ['model.int8.onnx', 'class_labels_indices.csv'],
    },
}


def fetch(url, part, limit=900 * 1024 * 1024):
    part.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={'User-Agent': 'DoubaoWork-AudioLocal/1.0'})
    total = 0
    with urllib.request.urlopen(req, timeout=60) as r, part.open('wb') as f:
        while chunk := r.read(1024 * 1024):
            total += len(chunk)
            if total > limit:
                raise ValueError('Download exceeds size limit')
            f.write(chunk)
    if not total:
        raise ValueError('Empty download')
    return total


def download_file(remote, dest, hosts):
    if dest.is_file() and dest.stat().st_size > 0:
        print(f'  already present: {dest.name}', flush=True)
        return
    part = dest.with_suffix(dest.suffix + '.part')
    last = None
    for host in hosts:
        url = f'{host}/{remote}'
        for attempt, pause in enumerate((0, 15, 40), start=1):
            if pause:
                time.sleep(pause)
            try:
                size = fetch(url, part)
                part.replace(dest)
                digest = hashlib.sha256(dest.read_bytes()).hexdigest()[:16]
                print(json.dumps({'file': dest.name, 'bytes': size, 'sha256_16': digest, 'from': host}, ensure_ascii=False), flush=True)
                return
            except urllib.error.HTTPError as e:
                last = e
                print(f'  {host} HTTP {e.code} (attempt {attempt}/3)', flush=True)
                if part.exists():
                    part.unlink()
                if e.code not in (429, 500, 502, 503, 504):
                    break
            except Exception as e:
                last = e
                print(f'  {host} {type(e).__name__} {str(e)[:80]} (attempt {attempt}/3)', flush=True)
                if part.exists():
                    part.unlink()
                break
    raise RuntimeError(f'model file unavailable: {dest.name}: {last}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dependencies', action='store_true')
    ap.add_argument('--models', action='store_true')
    ap.add_argument('--index-url', default='https://pypi.org/simple')
    ap.add_argument('--hosts', default=','.join(HOSTS))
    args = ap.parse_args()
    if not (args.dependencies or args.models):
        ap.error('Select --dependencies and/or --models')
    RUNTIME.mkdir(exist_ok=True)
    if args.dependencies:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--only-binary=:all:', '--target',
                        str(RUNTIME / 'deps'), '-r', str(ROOT / 'requirements.txt'),
                        '--index-url', args.index_url, '--disable-pip-version-check'], check=True)
    if args.models:
        hosts = [h.strip().rstrip('/') for h in args.hosts.split(',') if h.strip()]
        root = RUNTIME / 'models'
        for key, spec in MODELS.items():
            target = root / spec['dir']
            target.mkdir(parents=True, exist_ok=True)
            print(f'[{key}] {spec["repo"]}', flush=True)
            for name in spec['files']:
                download_file(f"{spec['repo']}/resolve/main/{name}", target / name, hosts)
        print('Models ready', flush=True)


if __name__ == '__main__':
    main()
