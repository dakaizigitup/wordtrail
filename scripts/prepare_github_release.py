"""Stage the already-tested Android APK and Windows patch for GitHub Releases.

The source archive must be regenerated with package_source.py after documentation
changes. Only explicitly listed Windows delivery files are packaged: personal
backups and install-result.json never enter release assets.
"""
from pathlib import Path
import argparse, hashlib, json, shutil, zipfile

ROOT = Path(__file__).resolve().parents[1]

def sha(file):
    with file.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--windows-patch-dir',type=Path,default=Path('D:/soft/英语输入法/电脑版四六级补词补丁'))
    parser.add_argument('--version',default='0.1.23')
    args = parser.parse_args()
    output = ROOT/'dist'/'github-release'
    output.mkdir(parents=True,exist_ok=True)
    patch = args.windows_patch_dir
    manifest = json.loads((patch/'SHA256.json').read_text(encoding='utf-8-sig'))
    for name,record in manifest['artifacts'].items():
        path = patch/name
        if path.stat().st_size != record['bytes'] or sha(path) != record['sha256']:
            raise ValueError('Windows patch checksum mismatch: '+name)
    version = manifest['version']
    windows = output/f'wordtrail-windows-ipa-{version}.zip'
    allowed = ['qingjian-server.exe','pronunciation-en.qj','dict.qj','install_desktop_ipa.ps1',
               'install.cmd','rollback.cmd','settings.cmd','vocabulary_settings.ps1','SHA256.json','NOTICE.txt','LICENSE','desktop-ipa.png']
    with zipfile.ZipFile(windows,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name in allowed:
            archive.write(patch/name,'wordtrail-windows-ipa-'+version+'/'+name)
        for source in [
            ROOT/'vocabulary/data/WIKTIONARY-ATTRIBUTION.md',
            ROOT/'vocabulary/data/batches/03-wiktionary-reviewed.tsv',
            ROOT/'vocabulary/data/batches/06-wiktionary-zh-reviewed.tsv',
            ROOT/'vocabulary/data/wiktionary-manifest-2.json',
            ROOT/'vocabulary/data/CC-CEDICT-ATTRIBUTION.md',
            ROOT/'vocabulary/data/batches/04-cc-cedict-reviewed.tsv',
            ROOT/'vocabulary/data/batches/05-cc-cedict-reviewed.tsv',
            ROOT/'vocabulary/data/batches/07-cc-cedict-review-input.tsv',
            ROOT/'vocabulary/data/batches/07-cc-cedict-reviewed.tsv',
            ROOT/'vocabulary/data/cccedict-manifest-3.json',
            ROOT/'vocabulary/data/batches/08-cc-cedict-candidate-decisions.tsv',
            ROOT/'vocabulary/data/batches/08-cc-cedict-candidate-summary.json',
            ROOT/'vocabulary/data/batches/08-cc-cedict-review-input.tsv',
            ROOT/'vocabulary/data/batches/08-cc-cedict-reviewed.tsv',
            ROOT/'vocabulary/data/cccedict-manifest-4.json',
            ROOT/'vocabulary/data/EXAM-TARGETS-ATTRIBUTION.md',
            ROOT/'vocabulary/data/batches/09-exam-target-reviewed.tsv',
            ROOT/'vocabulary/data/exam-target-ecdict-expansion.tsv',
            ROOT/'vocabulary/data/exam-target-kylebing-expansion.tsv',
            ROOT/'vocabulary/data/exam-target-manifest.json',
            ROOT/'vocabulary/data/ECDICT-LICENSE',
            ROOT/'vocabulary/data/KyleBing-LICENSE',
            ROOT/'vocabulary/data/OPENETYMOLOGY-DATA-ATTRIBUTION.md',
            ROOT/'vocabulary/data/OPENETYMOLOGY-DATA-LICENSE.txt',
            ROOT/'vocabulary/data/openetymology-exam-tags.tsv',
            ROOT/'vocabulary/data/openetymology-tags-manifest.json',
            ROOT/'vocabulary/data/openetymology-exam-expansion.tsv',
            ROOT/'vocabulary/data/openetymology-expansion-manifest.json',
            ROOT/'vocabulary/data/batches/10-openetymology-review-decisions.tsv',
            ROOT/'vocabulary/data/batches/10-openetymology-reviewed.tsv',
            ROOT/'vocabulary/data/batches/11-exam-target-reviewed.tsv',
            ROOT/'vocabulary/data/exam-target-batch-11-manifest.json',
            ROOT/'vocabulary/data/exam-target-batch-11-ecdict-expansion.tsv',
            ROOT/'vocabulary/data/exam-target-batch-11-kylebing-expansion.tsv',
            ROOT/'vocabulary/data/exam-target-batch-11-dual-expansion.tsv',
            ROOT/'vocabulary/data/exam-target-batch-11-cow-expansion.tsv',
            ROOT/'vocabulary/data/exam-target-batch-11-koreader-cow-expansion.tsv',
            ROOT/'vocabulary/data/exam-target-batch-11-cc-by-sa-expansion.tsv',
            ROOT/'vocabulary/data/pinyin-overlays/exam-target-batch-11.tsv',
            ROOT/'vocabulary/data/batches/12-ecdict-new-pinyin-reviewed.tsv',
            ROOT/'vocabulary/data/exam-target-batch-12-ecdict-expansion.tsv',
            ROOT/'vocabulary/data/exam-target-batch-12-manifest.json',
            ROOT/'vocabulary/data/pinyin-overlays/exam-target-batch-12.tsv',
            ROOT/'vocabulary/data/batches/13-exam-pinyin-reachability.tsv',
            ROOT/'vocabulary/data/exam-target-batch-13-manifest.json',
            ROOT/'vocabulary/data/pinyin-overlays/exam-target-batch-13.tsv',
            ROOT/'vocabulary/data/CHINESE-OPEN-WORDNET-LICENSE.txt',
            ROOT/'vocabulary/data/KOReader-LICENSE.txt',
            ROOT/'vocabulary/data/KOReader-ATTRIBUTION.txt',
            ROOT/'vocabulary/data/RIME-ICE-LICENSE.txt',
        ]:
            archive.write(source,'wordtrail-windows-ipa-'+version+'/data-license/'+source.name)
        archive.write(ROOT/'docs/电脑版音标补丁.md','wordtrail-windows-ipa-'+version+'/使用说明.md')
        for name in ['desktop-tests.json','desktop-tests.txt','desktop-installed-tests.json','pronunciation-tests.txt']:
            file=patch/'evidence'/name
            if file.is_file():
                archive.write(file,'wordtrail-windows-ipa-'+version+'/evidence/'+file.name)
    with zipfile.ZipFile(windows) as archive:
        if archive.testzip() is not None:
            raise ValueError('Windows ZIP CRC failed')
        names = archive.namelist()
        assert not any('/backup/' in n or n.endswith('install-result.json') for n in names)
    for name in [f'wordtrail-{args.version}-debug.apk',f'wordtrail-{args.version}-source.zip']:
        shutil.copy2(ROOT/'dist'/name,output/name)
    assets=[windows,output/f'wordtrail-{args.version}-debug.apk',output/f'wordtrail-{args.version}-source.zip']
    sums=''.join(sha(file)+'  '+file.name+'\n' for file in assets)
    (output/'SHA256SUMS.txt').write_text(sums,encoding='utf-8')
    records=[{'name':file.name,'bytes':file.stat().st_size,'sha256':sha(file)} for file in assets]
    (ROOT/'build/github-release-artifacts.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(records,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
