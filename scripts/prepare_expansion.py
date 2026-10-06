"""Build actual extra English translations from a pinned bilingual dictionary.

Use the first short Chinese gloss per POS, exact Chinese-key and compatible
base POS matching, no substring matching. All original translations remain.
The baseline is exported from the actual packed glossary, not assumed from TSV.
"""
from pathlib import Path
import collections,csv,hashlib,json,re,sys
from wordnet_guard import WordNetGuard

ROOT=Path(__file__).resolve().parents[1]
POS={'n':'n.','a':'adj.','adj':'adj.','v':'v.','vt':'v.','vi':'v.','adv':'adv.'}
BLOCK={'东西','某人','某物','事情','人们','事物'}
# rich has a wealth sense; affluent must not be attached to 丰富.
REJECT_PAIRS={('丰富','affluent')}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    guard=WordNetGuard(download='--download' in sys.argv)
    meta=json.loads((ROOT/'vocabulary/data/manifest.json').read_text(encoding='utf-8'))
    record=next(r for r in meta['input_files'] if r['path']=='ecdict.csv')
    source=ROOT/'build/vocabulary-research/skywind3000__ECDICT/ecdict.csv'
    if digest(source)!=record['sha256']:raise ValueError('ECDICT checksum mismatch')
    baseline=ROOT/'build/expansion-base.tsv'
    if not baseline.is_file():raise ValueError('Export actual packed glossary first; see vocabulary README')
    base={}
    for row in baseline.read_text(encoding='utf-8').splitlines():
        chinese,*senses=row.split('\t');parsed=[]
        for sense in senses:
            match=re.match(r'([a-z]+\.) (.+)$',sense)
            if match:parsed.append((match[2].strip().lower(),match[1]))
        base[chinese]=parsed
    tags={}
    for row in (ROOT/'vocabulary/data/english-tags.tsv').read_text(encoding='utf-8').splitlines():
        word,a,b=row.split('\t');tags[word]=int(a)|int(b)
    candidates=collections.defaultdict(dict);reject=collections.Counter()
    def add(chinese,english,pos,rank,origin):
        if (chinese,english) in REJECT_PAIRS:reject['reviewed_rejection']+=1;return
        if chinese not in base:reject['no_exact_base_key']+=1;return
        if english not in tags:reject['no_exam_membership']+=1;return
        if not re.fullmatch('[a-z]+(?:[-\'][a-z]+)*',english):reject['nonword']+=1;return
        originals=base[chinese]
        if originals and pos not in {p for _,p in originals}:reject['incompatible_pos']+=1;return
        if any(word==english for word,_ in originals):reject['already_in_packed_glossary']+=1;return
        if origin=='ECDICT' and not guard.related(english,pos,originals):reject['no_wordnet_synonym_relation']+=1;return
        old=candidates[chinese].get(english)
        if old is None or rank<old[0]:candidates[chinese][english]=(rank,pos,origin)
    with source.open(encoding='utf-8-sig',newline='') as stream:
        for row in csv.DictReader(stream):
            english=row['word'].strip()
            if english not in tags or english!=english.lower():continue
            rank=int(row.get('frq') or row.get('bnc') or 999999) or 999999
            for meaning in row['translation'].replace('\\n','\n').splitlines():
                match=re.match(r'^([a-z]+)\.\s*(.+)$',meaning.strip())
                if not match or match[1] not in POS:continue
                pos=POS[match[1]];chinese=re.split('[,，;；]',match[2],maxsplit=1)[0].strip()
                if chinese in BLOCK or not re.fullmatch('[\u4e00-\u9fff]{2,6}',chinese):reject['non_atomic_gloss']+=1;continue
                if pos=='adj.' and chinese.endswith('的') and chinese not in base:chinese=chinese[:-1]
                if len(chinese)<2:continue
                add(chinese,english,pos,rank,'ECDICT')
    reviewed=ROOT/'vocabulary/data/reviewed-expansion.tsv'
    for row in reviewed.read_text(encoding='utf-8').splitlines():
        if row and not row.startswith('#'):
            chinese,english,pos=row.split('\t');add(chinese,english,pos,0,'Wordtrail-reviewed')
    rows=[];winners=[]
    for chinese,items in sorted(candidates.items()):
        for english,(rank,pos,origin) in sorted(items.items(),key=lambda p:(p[1][0],p[0]))[:8]:
            rows.append((chinese,english,pos,origin))
        original_words=[w for w,_ in base[chinese]]
        for bit,(code,_) in enumerate([(t['id'],t['label']) for t in meta['tags']]):
            if not any(tags.get(w,0)&(1<<bit) for w in original_words):
                extra=[english for c,english,_,_ in rows[-8:] if c==chinese and tags[english]&(1<<bit)]
                if extra:winners.append(dict(chinese=chinese,target=code,added=extra,original=original_words))
    payload=''.join('\t'.join(row)+'\n' for row in rows).encode('utf-8')
    output=ROOT/'vocabulary/data/english-expansion.tsv';output.write_bytes(payload)
    actual_words={w for senses in base.values() for w,_ in senses}
    new_words={w for _,w,_,_ in rows};stats={
        'version':1,'source':record,'source_license':'MIT; vocabulary/data/ECDICT-LICENSE','wordnet_validation':guard.meta,
        'packed_glossary_sha256':digest(ROOT/'data/glossary-en.qj'),'baseline_export_sha256':digest(baseline),
        'reviewed_pairs_sha256':digest(reviewed),'baseline_chinese_entries':len(base),
        'chinese_entries_extended':len({c for c,_,_,_ in rows}),'added_translation_pairs':len(rows),
        'added_headwords':len(new_words),'headwords_not_anywhere_in_original_glossary':len(new_words-actual_words),
        'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest(),
        'by_target':{t['id']:sum(bool(tags[w]&(1<<i)) for _,w,_,_ in rows) for i,t in enumerate(meta['tags'])},
        'reviewed_pairs_shipped':sum(s=='Wordtrail-reviewed' for _,_,_,s in rows),
        'rules':'First atomic Chinese gloss per POS; exact existing Chinese key; compatible POS; automatic additions must share WordNet synsets or adjective similar-to links with original senses. Reviewed mappings bypass synonym restriction. Adjective 的 may be removed only to match existing key; retain originals; deduplicate English headwords; maximum 8 additions per key; no examples, phrases, substring or stemming.',
        'rejected':dict(reject),'quality_scope':'Community bilingual meanings, conservatively filtered, not all manually reviewed; ambiguous meanings can be corrected in reviewed mappings.',
    }
    (ROOT/'vocabulary/data/expansion-manifest.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'build/expansion-new-priority-examples.json').write_text(json.dumps(winners,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:stats[k] for k in ['chinese_entries_extended','added_translation_pairs','added_headwords','headwords_not_anywhere_in_original_glossary','bytes','reviewed_pairs_shipped']},indent=2))
    print(json.dumps(winners[:12],ensure_ascii=False,indent=2))

if __name__=='__main__':main()
