"""Restore pinned build inputs from the matching complete-source release.

Only dependency/data paths are extracted; authored source is never overwritten.
No models or SDK tools are downloaded here. prepare_voice.py handles pinned ASR.
"""
from pathlib import Path, PurePosixPath
import argparse, hashlib, re, shutil, urllib.request, zipfile

ROOT = Path(__file__).resolve().parents[1]
RELEASE = 'https://github.com/dakaizigitup/wordtrail/releases/download/v0.1.13/'
NAME = 'wordtrail-0.1.13-source.zip'
PREFIXES = ('third-party/rust-ipa/', 'third-party/sherpa-onnx/jniLibs/')

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def restore(archive):
    count = 0
    with zipfile.ZipFile(archive) as source:
        for entry in source.infolist():
            if entry.is_dir() or not entry.filename.startswith('wordtrail-mobile/'):
                continue
            relative = entry.filename.removeprefix('wordtrail-mobile/')
            if not (relative.startswith(PREFIXES) or
                    (relative.startswith('data/') and relative.endswith('.qj'))):
                continue
            parts = PurePosixPath(relative).parts
            if '..' in parts or '\\' in relative or ':' in relative:
                raise ValueError('Unsafe archive member')
            target = ROOT.joinpath(*parts).resolve()
            if not target.is_relative_to(ROOT.resolve()):
                raise ValueError('Archive member outside project')
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.open(entry) as data, target.open('wb') as output:
                shutil.copyfileobj(data, output)
            count += 1
    if not count:
        raise ValueError('No dependency files found')
    print(f'Restored {count} dependency/data files; authored source preserved.')
    import subprocess, sys
    subprocess.run([sys.executable, str(ROOT/'scripts/apply_upstream.py')], check=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-zip', type=Path, help='Matching complete-source ZIP already downloaded')
    args = parser.parse_args()
    if not (ROOT/'vendor/qingjian/crates/qingjian-core/Cargo.toml').is_file():
        raise SystemExit('Initialize pinned upstream first: git submodule update --init --recursive')
    if args.source_zip:
        restore(args.source_zip)
        return
    cache = ROOT/'build'/'release-inputs'
    cache.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(RELEASE+'SHA256SUMS.txt', headers={'User-Agent':'Wordtrail-build'})
    with urllib.request.urlopen(request, timeout=60) as response:
        sums = response.read().decode('utf-8')
    match = re.search(r'^([0-9a-fA-F]{64})\s+\*?'+re.escape(NAME)+r'\s*$', sums, re.MULTILINE)
    if not match:
        raise ValueError('Complete-source checksum missing')
    archive = cache/NAME
    if not archive.is_file() or digest(archive) != match.group(1).lower():
        temporary = cache/(NAME+'.part')
        urllib.request.urlretrieve(RELEASE+NAME, temporary)
        if digest(temporary) != match.group(1).lower():
            raise ValueError('Complete-source SHA-256 mismatch')
        temporary.replace(archive)
    restore(archive)

if __name__ == '__main__':
    main()
