"""Build a pinned, independent UK/US IPA dictionary without changing translation data."""
from pathlib import Path
import hashlib,json,subprocess

ROOT=Path(__file__).resolve().parents[1]

def digest(file):
    with file.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def prepare():
    source=ROOT/'pronunciation/source'
    provenance=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
    for name,expected in provenance['files'].items():
        assert digest(source/Path(name).name)==expected['sha256'], 'IPA source checksum mismatch: '+name
    target=ROOT/'data/pronunciation-en.qj'; manifest=ROOT/'data/pronunciation-manifest.json'
    if target.exists() and manifest.exists():
        previous=json.loads(manifest.read_text(encoding='utf-8'))
        if previous.get('source_commit')==provenance['commit'] and previous.get('sha256')==digest(target):return previous
    entries={};counts={}
    for region in ('UK','US'):
        count=0
        for line in (source/f'en_{region}.txt').read_text(encoding='utf-8').splitlines():
            if not line.strip():continue
            word,ipa=line.split('\t',1);word=word.strip().lower();ipa=ipa.strip()
            if not word or not ipa or '\t' in ipa or '|' in ipa:raise ValueError('Invalid IPA source row')
            entries.setdefault(word,{})[region]=ipa;count+=1
        counts[region]=count
    generated=ROOT/'build/pronunciation-en.tsv';generated.parent.mkdir(parents=True,exist_ok=True)
    generated.write_text(''.join(word+'\t'+'\t'.join(ipa+'|'+region for region,ipa in sorted(values.items()))+'\n' for word,values in sorted(entries.items())),encoding='utf-8')
    subprocess.run(['cargo','run','--locked','--offline','-p','wordtrail-pronunciation','--bin','pack-pronunciation','--',str(generated),str(target)],cwd=ROOT,check=True)
    result={'source_commit':provenance['commit'],'entries':len(entries),'source_rows':counts,'bytes':target.stat().st_size,'sha256':digest(target),'UK_license':'GPL-3.0-only','US_license':'MIT'}
    manifest.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':print(json.dumps(prepare(),ensure_ascii=False,indent=2))
