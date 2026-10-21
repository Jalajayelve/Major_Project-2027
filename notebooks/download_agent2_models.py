"""Download pinned public BAAI weights into the project's ignored cache."""
from pathlib import Path
import hashlib
import json
import requests

ROOT = Path(__file__).resolve().parents[1]
MODELS = {
    'BAAI/bge-small-en-v1.5': '5c38ec7c405ec4b44b94cc5a9bb96e735b38267a',
    'BAAI/bge-reranker-base': '2cfc18c9415c912f9d8155881c133215df768a70',
}


def download():
    session = requests.Session()
    session.trust_env = False
    for repo, revision in MODELS.items():
        dest = ROOT / '.cache' / 'agent2' / repo.split('/')[-1]
        dest.mkdir(parents=True, exist_ok=True)
        response = session.get(f'https://huggingface.co/api/models/{repo}/revision/{revision}', timeout=60)
        response.raise_for_status()
        manifest = {'repo': repo, 'revision': revision, 'files': {}}
        for item in response.json()['siblings']:
            name = item['rfilename']
            if name.startswith('onnx/') or name in ['pytorch_model.bin', '.gitattributes', 'README.md']:
                continue
            path = dest / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                print('Downloading', repo, name, flush=True)
                with session.get(f'https://huggingface.co/{repo}/resolve/{revision}/{name}', stream=True, timeout=120) as r:
                    r.raise_for_status()
                    tmp = path.with_suffix(path.suffix + '.partial')
                    with tmp.open('wb') as f:
                        for chunk in r.iter_content(1024 * 1024):
                            f.write(chunk)
                    tmp.replace(path)
            manifest['files'][name] = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
        (dest / 'download_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        print('Ready:', repo, revision, flush=True)


if __name__ == '__main__':
    download()
