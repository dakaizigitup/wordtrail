"""Build the shipped headword/tag index from pinned, checksum-verified sources.

Only headwords and membership are extracted; definitions, examples and audio
are not redistributed. Run --download to populate the ignored source cache.
"""
from pathlib import Path
import argparse, collections, csv, hashlib, json, urllib.request

ROOT = Path(__file__).resolve().parents[1]
TAGS = ('cet4', 'cet6', 'tem4', 'tem8', 'toefl', 'ielts')
LABELS = ('四级', '六级', '专四', '专八', '托福', '雅思')
REPOS = ('skywind3000/ECDICT', 'KyleBing/english-vocabulary')

def normalize(word):
    word = word.strip().lower()
    if not word or any(c in word for c in '\t\r\n\0'):
        raise ValueError('Invalid headword')
    return word

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT/'build/vocabulary-research')
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    research = json.loads((ROOT/'docs/research/vocabulary-sources.json').read_text(encoding='utf-8'))
    sources = [s for s in research['sources'] if s['repo'] in REPOS]
    # File records are separated from repository metadata in the research manifest.
    files = research['inspected_data_files']
    wanted = []
    for source in sources:
        records = source['checked_root_files'] + [r for r in files if r['repo'] == source['repo']]
        for record in records:
            if record['path'] == 'LICENSE' or record['path'] == 'ecdict.csv' or (
                record['path'].startswith('full_line_jsonl/simple/正序/') and
                Path(record['path']).stem in LABELS
            ):
                wanted.append(dict(record, repo=source['repo']))
    if len(wanted) != 9:
        raise ValueError('Expected CSV, six JSONL files and two licenses')
    for record in wanted:
        path = args.cache/record['repo'].replace('/', '__')/record['path']
        if not path.is_file() and args.download:
            path.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(record['url'], timeout=120) as response:
                payload = response.read()
            if hashlib.sha256(payload).hexdigest() != record['sha256']:
                raise ValueError('Download checksum mismatch: '+record['path'])
            path.write_bytes(payload)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('Missing or changed source; use --download: '+str(path))
    index = {}
    def add(word, mask, source):
        entry = index.setdefault(normalize(word), [0, 0])
        entry[source] |= mask
    with (args.cache/'skywind3000__ECDICT/ecdict.csv').open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            mask = sum(1 << TAGS.index(tag) for tag in set(row.get('tag', '').split()) if tag in TAGS)
            if mask:
                add(row['word'], mask, 0)
    rows = {}
    for label, tag in zip(LABELS, TAGS):
        path = args.cache/'KyleBing__english-vocabulary/full_line_jsonl/simple/正序'/f'{label}.jsonl'
        count = 0
        with path.open(encoding='utf-8') as stream:
            for line in stream:
                if line.strip():
                    add(json.loads(line)['word'], 1 << TAGS.index(tag), 1)
                    count += 1
        rows[tag] = count
    output = ROOT/'vocabulary/data'
    output.mkdir(parents=True, exist_ok=True)
    payload = ''.join(f'{word}\t{a}\t{b}\n' for word, (a, b) in sorted(index.items())).encode('utf-8')
    (output/'english-tags.tsv').write_bytes(payload)
    for repo, name in zip(REPOS, ('ECDICT-LICENSE', 'KyleBing-LICENSE')):
        (output/name).write_bytes((args.cache/repo.replace('/', '__')/'LICENSE').read_bytes())
    manifest = {
        'version': 1, 'normalization': 'trim and Unicode lowercase; exact whole-headword match; no stemming or substring tags',
        'columns': ['headword', 'ecdict_tag_mask', 'kylebing_tag_mask'],
        'tags': [dict(id=t, bit=i, label=l, words=sum(bool((a|b)&(1<<i)) for a,b in index.values())) for i,(t,l) in enumerate(zip(TAGS,LABELS))],
        'words': len(index), 'multiple_tag_words': sum((a|b).bit_count()>1 for a,b in index.values()),
        'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest(),
        'sources': [dict(repo=s['repo'], commit=s['commit'], license=s['root_license']) for s in sources],
        'input_files': wanted, 'kylebing_rows_before_deduplication': rows,
        'scope': 'Community wordlist membership, not official complete exam coverage or word difficulty. Only headwords/tags extracted; no source definitions, examples or audio.'
    }
    (output/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:manifest[k] for k in ('words','multiple_tag_words','bytes','sha256')}, indent=2))

if __name__ == '__main__':
    main()
