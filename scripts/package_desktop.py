"""Package the tested enhancement for an existing official Windows 0.1.4 install."""
from pathlib import Path
import hashlib, json, shutil

ROOT=Path(__file__).resolve().parents[1]
DELIVERY=Path('D:/soft/英语输入法/电脑版四六级补词补丁')
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def main():
    DELIVERY.mkdir(parents=True,exist_ok=True)
    previous_manifest_path=DELIVERY/'SHA256.json'
    previous_manifest=json.loads(previous_manifest_path.read_text(encoding='utf-8-sig')) if previous_manifest_path.is_file() else {}
    for source,name in [(ROOT/'target/release/qingjian-server.exe','qingjian-server.exe'),(ROOT/'data/pronunciation-en.qj','pronunciation-en.qj'),(ROOT/'data/generated/dict.qj','dict.qj'),(ROOT/'scripts/install_desktop_ipa.ps1','install_desktop_ipa.ps1'),(ROOT/'desktop/NOTICE.txt','NOTICE.txt'),(ROOT/'LICENSE','LICENSE')]:
        shutil.copy2(source,DELIVERY/name)
    data_license=DELIVERY/'data-license';data_license.mkdir(parents=True,exist_ok=True)
    for source in [
        ROOT/'vocabulary/data/WIKTIONARY-ATTRIBUTION.md',
        ROOT/'vocabulary/data/batches/03-wiktionary-reviewed.tsv',
        ROOT/'vocabulary/data/batches/06-wiktionary-zh-reviewed.tsv',
        ROOT/'vocabulary/data/wiktionary-manifest-2.json',
        ROOT/'vocabulary/data/professional-domain-tags.tsv',
        ROOT/'vocabulary/data/professional-expansion.tsv',
        ROOT/'vocabulary/data/professional-vocabulary-manifest.json',
        ROOT/'vocabulary/data/batches/14-professional-reviewed.tsv',
        ROOT/'vocabulary/data/batches/14-professional-domain-evidence.tsv',
        ROOT/'vocabulary/data/CJK-COMPSCI-ATTRIBUTION.md',
        ROOT/'vocabulary/data/cjk-compsci-tags.tsv',
        ROOT/'vocabulary/data/cjk-compsci-expansion.tsv',
        ROOT/'vocabulary/data/cjk-compsci-manifest.json',
        ROOT/'vocabulary/data/batches/15-cjk-compsci-reviewed.tsv',
        ROOT/'vocabulary/data/batches/15-cjk-compsci-evidence.tsv',
        ROOT/'vocabulary/data/sources/cjk-compsci-terms/LICENSE',
        ROOT/'vocabulary/data/FIBO-ATTRIBUTION.md',
        ROOT/'vocabulary/data/fibo-business-tags.tsv',
        ROOT/'vocabulary/data/fibo-business-manifest.json',
        ROOT/'vocabulary/data/batches/16-fibo-business-reviewed.tsv',
        ROOT/'vocabulary/data/batches/16-fibo-business-candidates.tsv',
        ROOT/'vocabulary/data/sources/fibo/LICENSE',
        ROOT/'vocabulary/data/BETTER-QUANT-ATTRIBUTION.md',
        ROOT/'vocabulary/data/better-quant-business-tags.tsv',
        ROOT/'vocabulary/data/better-quant-expansion.tsv',
        ROOT/'vocabulary/data/better-quant-manifest.json',
        ROOT/'vocabulary/data/batches/17-better-quant-reviewed.tsv',
        ROOT/'vocabulary/data/batches/17-better-quant-candidates.tsv',
        ROOT/'vocabulary/data/sources/better-quant-wiki/LICENSE',
        ROOT/'vocabulary/data/CFPB-ATTRIBUTION.md',
        ROOT/'vocabulary/data/cfpb-finance-tags.tsv',
        ROOT/'vocabulary/data/cfpb-finance-expansion.tsv',
        ROOT/'vocabulary/data/cfpb-finance-manifest.json',
        ROOT/'vocabulary/data/batches/18-cfpb-finance-reviewed.tsv',
        ROOT/'vocabulary/data/batches/18-cfpb-finance-candidates.tsv',
        ROOT/'vocabulary/data/sources/cfpb/cfpb-financial-glossary-2024.md',
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
        ROOT/'vocabulary/data/OPENETYMOLOGY-CET-DATA-ATTRIBUTION.md',
        ROOT/'vocabulary/data/openetymology-cet-tags.tsv',
        ROOT/'vocabulary/data/openetymology-cet-tags-manifest.json',
        ROOT/'vocabulary/data/openetymology-cet-expansion.tsv',
        ROOT/'vocabulary/data/openetymology-cet-manifest.json',
        ROOT/'vocabulary/data/batches/29-openetymology-cet-candidates.tsv',
        ROOT/'vocabulary/data/batches/29-openetymology-cet-review.tsv',
        ROOT/'vocabulary/data/batches/29-openetymology-cet-reviewed.tsv',
        ROOT/'scripts/build_openetymology_cet_tags.py',
        ROOT/'scripts/build_openetymology_cet_batch.py',
        ROOT/'docs/29-OpenEtymology四六级补词.md',
        ROOT/'vocabulary/data/batches/10-openetymology-review-decisions.tsv',
        ROOT/'vocabulary/data/batches/10-openetymology-reviewed.tsv',
        ROOT/'vocabulary/data/EXAM-TARGETS-ATTRIBUTION.md',
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
        ROOT/'vocabulary/data/ECDICT-LICENSE',
        ROOT/'vocabulary/data/KyleBing-LICENSE',
        ROOT/'vocabulary/data/CHINESE-OPEN-WORDNET-LICENSE.txt',
        ROOT/'vocabulary/data/KOReader-LICENSE.txt',
        ROOT/'vocabulary/data/KOReader-ATTRIBUTION.txt',
        ROOT/'vocabulary/data/RIME-ICE-LICENSE.txt',
        ROOT/'vocabulary/data/NAER-LIFE-SCIENCE-ATTRIBUTION.md',
        ROOT/'vocabulary/data/naer-life-science-expansion.tsv',
        ROOT/'vocabulary/data/naer-life-science-tags.tsv',
        ROOT/'vocabulary/data/naer-life-science-manifest.json',
        ROOT/'vocabulary/data/batches/26-naer-life-science-prefilter.tsv',
        ROOT/'vocabulary/data/batches/26-naer-life-science-candidates.tsv',
        ROOT/'vocabulary/data/batches/26-naer-life-science-reviewed.tsv',
        ROOT/'vocabulary/data/sources/naer/life-science-dataset.json',
        ROOT/'vocabulary/data/sources/naer/life-science-academic-terms.csv',
        ROOT/'scripts/build_naer_life_science_batch.py',
        ROOT/'docs/26-NAER生命科学词汇.md',
        ROOT/'vocabulary/data/NAER-VETERINARY-ATTRIBUTION.md',
        ROOT/'vocabulary/data/naer-veterinary-expansion.tsv',
        ROOT/'vocabulary/data/naer-veterinary-tags.tsv',
        ROOT/'vocabulary/data/naer-veterinary-manifest.json',
        ROOT/'vocabulary/data/batches/27-naer-veterinary-prefilter.tsv',
        ROOT/'vocabulary/data/batches/27-naer-veterinary-candidates.tsv',
        ROOT/'vocabulary/data/batches/27-naer-veterinary-reviewed.tsv',
        ROOT/'vocabulary/data/sources/naer/veterinary-dataset.json',
        ROOT/'vocabulary/data/sources/naer/veterinary-academic-terms.csv',
        ROOT/'scripts/build_naer_veterinary_batch.py',
        ROOT/'docs/27-NAER兽医学词汇.md',
        ROOT/'vocabulary/data/NAER-ECONOMICS-ATTRIBUTION.md',
        ROOT/'vocabulary/data/naer-economics-expansion.tsv',
        ROOT/'vocabulary/data/naer-economics-tags.tsv',
        ROOT/'vocabulary/data/naer-economics-manifest.json',
        ROOT/'vocabulary/data/batches/30-naer-economics-prefilter.tsv',
        ROOT/'vocabulary/data/batches/30-naer-economics-candidates.tsv',
        ROOT/'vocabulary/data/batches/30-naer-economics-reviewed.tsv',
        ROOT/'vocabulary/data/sources/naer/economics-dataset.json',
        ROOT/'vocabulary/data/sources/naer/economics-academic-terms-2025-12-16.csv',
        ROOT/'scripts/build_naer_economics_batch.py',
        ROOT/'docs/30-NAER经济学术语补充.md',
        ROOT/'vocabulary/data/WORDLEVEL-ATTRIBUTION.md',
        ROOT/'vocabulary/data/wordlevel-toefl-ielts-expansion.tsv',
        ROOT/'vocabulary/data/wordlevel-toefl-ielts-tags.tsv',
        ROOT/'vocabulary/data/wordlevel-toefl-ielts-manifest.json',
        ROOT/'vocabulary/data/batches/28-wordlevel-reviewed.tsv',
        ROOT/'vocabulary/data/batches/28-wordlevel-tag-evidence.tsv',
        ROOT/'vocabulary/data/sources/wordlevel/LICENSE',
        ROOT/'vocabulary/data/sources/wordlevel/README.md',
        ROOT/'vocabulary/data/sources/wordlevel/toefl_essential_vocabulary.csv',
        ROOT/'scripts/build_wordlevel_toefl_batch.py',
        ROOT/'docs/28-WordLevel考试词汇.md',
    ]:
        try:
            relative=source.relative_to(ROOT/'vocabulary/data')
        except ValueError:
            relative=None
        destination=data_license/relative if relative and relative.parts[0]=='sources' else data_license/source.name
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,destination)
    original='c9c3ac98a5b51f57fcbfd8ccec8ed25a96502592b7a40b498bc2a6447c54e554'
    shutil.copy2(ROOT/'scripts/vocabulary_settings.ps1',DELIVERY/'vocabulary_settings.ps1')
    (DELIVERY/'settings.cmd').write_text('@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0vocabulary_settings.ps1"\r\n',encoding='ascii')
    supported=['b3b7100268fa64a89560f2142038623ac9527fa7875149ed68caec4aaf625634','a08ac3fa0b4a151d8b5e0bf18b21bc545c5360f2f623e031867645c147ca1b18','2fcb6f5b467fc0dce46777fdb1723c807e04712c84c9e25718e43880e817396d','2ef3aa287d6987795877c28e1d6b2be55f7e017f2a687a3693e40a31b230b6d7','e68aa1eabd3689f0e749acd82516d36f9db12d1e9e1c451e1525a8362b1cd703','0f5e0aaaeaacc97879a1003ca08adfc907919867dc249e4e64912560d826fb8f','f4ea6155c89d2537bfb1c8a2fd99783e4367a332b022819ac9a535657fe8b2bd','31fe230e9c4e86ea2713b97ef37e61743804aa277db61466e7210bdccb827ccb','c1f0164589343b3db2b2c9d43018d9fa38baffa402ef4343e2035cb5dc8291c4','ba55c5d9fb619935704dd8a205d88bea6732ef6ae32bdf39d813e1a0f513fa6f','30bb3b9e6aad17b2779570dbb4366df0827432cf49129743a5af336a77792de8','4ec9c04a27f11abbbaf6d938715602a5a6e30e1a19e58572a37976a03d9dee7b']
    previous_server=previous_manifest.get('artifacts',{}).get('qingjian-server.exe',{}).get('sha256')
    if previous_server and previous_server not in supported and previous_server != original:supported.append(previous_server)
    manifest=dict(version='0.1.22',base_version='Qingjian Windows 0.1.4',original_server_sha256=original,supported_previous_server_sha256=supported,
                  original_dictionary_sha256='3e33b16a84df555e6f16d52ac8ab3c2c6b6f1f71734e69463861fd5abd9c19dc',
                  supported_previous_dictionary_sha256=['07a4ce7fc57b45ca49fd7e5474d555c72c722c7f084d83cf9a08eecbd7c65157'],artifacts={})
    for name in ['qingjian-server.exe','pronunciation-en.qj','dict.qj','install_desktop_ipa.ps1','vocabulary_settings.ps1','settings.cmd']:
        path=DELIVERY/name
        manifest['artifacts'][name]=dict(bytes=path.stat().st_size,sha256=sha(path))
    (DELIVERY/'SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    for name,extra in [('install.cmd',''),('rollback.cmd',' -Rollback')]:
        (DELIVERY/name).write_text('@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_desktop_ipa.ps1"'+extra+'\r\n',encoding='ascii')
    shutil.copy2(ROOT/'docs/电脑版音标补丁.md',DELIVERY/'使用说明.md')
    evidence=DELIVERY/'evidence';evidence.mkdir(exist_ok=True)
    for name in ['desktop-tests.json','desktop-tests.txt','desktop-installed-tests.json','pronunciation-tests.txt']:
        source=ROOT/'build'/name
        if source.is_file():shutil.copy2(source,evidence/name)
    shutil.copy2(ROOT/'docs/screenshots/desktop-0.1.4-default.png',DELIVERY/'desktop-ipa.png')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
