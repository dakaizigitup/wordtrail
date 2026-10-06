"""复制经过官方安装器校验的数据，或从固定的官方 data-v2 包读取。"""
from pathlib import Path
import argparse, hashlib, json, shutil, tarfile, urllib.request

ROOT = Path(__file__).resolve().parents[1]
FILES = ('dict.qj', 'glossary-en.qj', 'glossary-ja.qj', 'glossary-es.qj')
URL = 'https://github.com/qingjian-team/qingjian/releases/download/data-v2/qingjian-data.tar.gz'
SHA256 = '4d59fdb3f82809736beebe23b42cec283ffd87f6a8f0243b95291c460f1f0caa'
EXPECTED = {
    'dict.qj': '3e33b16a84df555e6f16d52ac8ab3c2c6b6f1f71734e69463861fd5abd9c19dc',
    'glossary-en.qj': '4cc9c587b206d0f12aabb1b85cb21e6ac2a1c8c4932b9af14332bd96e0be012a',
    'glossary-ja.qj': 'ec41e4983bf46c0366124afb5285dba14f5c1ee425bd55d9a9f5518d93256933',
    'glossary-es.qj': '13f5fbda3f1295c5946ddde5e57017f0689f2dd985a951c5bffaf821cb421865',
}

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

def copy_data(source,target):
    # 已加载的 mmap 在 Windows 上不能覆盖；内容相同就直接复用。
    if target.is_file() and source.stat().st_size==target.stat().st_size and digest(source)==digest(target): return
    shutil.copy2(source,target)

def prepare(source):
    canonical = ROOT / 'data'
    canonical.mkdir(exist_ok=True)
    if source and all((source / name).is_file() for name in FILES):
        for name in FILES:
            if digest(source/name) != EXPECTED[name]: raise RuntimeError(f'Pinned data SHA-256 mismatch: {source/name}')
            copy_data(source / name, canonical / name)
        provenance = 'qingjian v0.1.4 pinned official data (verified per-file SHA-256)'
    elif not all((canonical / name).is_file() for name in FILES):
        archive = ROOT / 'build' / 'qingjian-data-v2.tar.gz'
        archive.parent.mkdir(exist_ok=True)
        if not archive.is_file(): urllib.request.urlretrieve(URL, archive)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
            raise RuntimeError('Official data archive SHA-256 mismatch')
        with tarfile.open(archive) as tar:
            for name in FILES:
                members = [m for m in tar.getmembers() if m.isfile() and Path(m.name).name == name]
                if len(members) != 1: raise RuntimeError(f'Missing or ambiguous data: {name}')
                with tar.extractfile(members[0]) as source_file, (canonical/name).open('wb') as target:
                    shutil.copyfileobj(source_file, target)
        provenance = URL
    else:
        provenance = 'qingjian v0.1.4 pinned local data (verified per-file SHA-256)'
    for name in FILES:
        if digest(canonical/name) != EXPECTED[name]: raise RuntimeError(f'Pinned data SHA-256 mismatch: {name}')
    from prepare_runtime_dictionary import prepare as prepare_runtime
    runtime_dictionary = prepare_runtime(export=False, do_pack=False)
    runtime_dict = ROOT/'build/runtime-data/dict.qj'
    from prepare_pronunciation import prepare as prepare_ipa
    ipa=prepare_ipa()
    for target in (ROOT/'android/app/src/main/assets/data', ROOT/'ios/Keyboard/Data', ROOT/'data/generated'):
        target.mkdir(parents=True, exist_ok=True)
        for name in FILES:
            copy_data(runtime_dict if name == 'dict.qj' else canonical/name, target/name)
        copy_data(canonical/'pronunciation-en.qj',target/'pronunciation-en.qj')
    manifest = {'upstream_version':'0.1.4', 'source':provenance, 'files':{}}
    levels=ROOT/'vendor/qingjian/assets/levels/levels-en.tsv'
    levels_sha='a5f810f7f8788d6c7b6ed11fd849ae0d31f6a5d9d953ab9528798d9b11d27ffa'
    if digest(levels)!=levels_sha:raise RuntimeError('Pinned CEFR table SHA-256 mismatch')
    manifest['vocabulary_levels']={'scheme':'CEFR A1-C2','entries':8845,'sha256':levels_sha,'embedded_in':'native engine','source':'CEFR-J 1.5 / Octanove C1-C2 1.0; vendor/qingjian/assets/levels/README.md'}
    for name in FILES:
        path=canonical/name
        manifest['files'][name]={'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    manifest['files']['pronunciation-en.qj']={'bytes':ipa['bytes'],'sha256':ipa['sha256'],'source':'independent IPA dictionary; see pronunciation-manifest.json'}
    manifest['runtime_dictionary'] = runtime_dictionary
    manifest['source_files'] = {'dict.qj': {'bytes':(canonical/'dict.qj').stat().st_size,
                                             'sha256':digest(canonical/'dict.qj'),
                                             'role':'pinned, unmodified upstream input'}}
    (canonical/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,default=Path('C:/Program Files/Qingjian/data/generated'))
    prepare(parser.parse_args().source)
