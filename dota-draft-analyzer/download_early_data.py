"""Download the pinned public mirror, check SHA-256, extract a single CSV."""
import hashlib
import io
import json
import zipfile
import requests
from common import ROOT


def main():
    folder = ROOT / 'data/early'
    source = json.loads((folder / 'SOURCE.json').read_text(encoding='utf-8'))
    response = requests.get(source['download_url'], timeout=120)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        data = archive.read('features.csv')
    if hashlib.sha256(data).hexdigest() != source['sha256']:
        raise ValueError('Downloaded dataset checksum does not match the pinned source')
    (folder / 'features.csv').write_bytes(data)
    print('Verified data/early/features.csv')


if __name__ == '__main__':
    main()
