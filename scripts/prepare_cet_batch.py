"""构建批次01：保留已发布扩词，补四六级完整短义项，记录覆盖和待核对项。"""
from pathlib import Path
import argparse
import collections
import csv
import hashlib
import json
import re

from prepare_expansion import BLOCK, POS, REJECT_PAIRS
from wordnet_guard import WordNetGuard

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'vocabulary/data'
BATCH = DATA / 'batches'
LIMIT = 8
WORD = re.compile(r"[a-z]+(?:[-'][a-z]+)*")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_base(path):
    base = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        chinese, *raw = line.split('\t')
        parsed = []
        for sense in raw:
            match = re.match(r'([a-z]+\.) (.+)$', sense)
            if match:
                parsed.append((match[2].strip().lower(), match[1]))
            elif sense.startswith(' ') and sense.strip():
                # 导出器用空词性前缀表示原表未标词性；覆盖统计仍须保留词面。
                parsed.append((sense.strip().lower(), ''))
            else:
                raise ValueError('Unrecognized baseline sense: ' + sense)
        base[chinese] = parsed
    return base


def atomic_glosses(translation, base):
    """只按释义列表分隔符拆分；不剥括号，不从解释中抽取子串。"""
    for line in translation.replace('\\n', '\n').splitlines():
        match = re.match(r'^([a-z]+)\.\s*(.+)$', line.strip())
        if not match or match[1] not in POS:
            continue
        pos = POS[match[1]]
        for gloss in re.split('[,，;；]', match[2]):
            chinese = gloss.strip()
            if pos == 'adj.' and chinese.endswith('的') and chinese not in base and chinese[:-1] in base:
                chinese = chinese[:-1]
            if chinese not in BLOCK and re.fullmatch(r'[\u4e00-\u9fff]{2,6}', chinese):
                yield chinese, pos


def coverage(tags, words, ipa):
    result = {}
    for bit, code in enumerate(('cet4', 'cet6', 'tem4', 'tem8', 'toefl', 'ielts')):
        target = {w for w, mask in tags.items() if mask & (1 << bit)}
        mapped = target & words
        result[code] = dict(total=len(target), mapped=len(mapped), missing=len(target - words),
                            percent=round(100 * len(mapped) / len(target), 2),
                            mapped_with_ipa=len(mapped & ipa))
    return result


def make_batch():
    meta = json.loads((DATA / 'manifest.json').read_text(encoding='utf-8'))
    seed_meta = json.loads((BATCH / '00-manifest.json').read_text(encoding='utf-8'))
    seed = BATCH / '00-expansion.tsv'
    baseline = ROOT / 'build/expansion-base.tsv'
    for path, expected in [(seed, seed_meta['sha256']),
                           (baseline, seed_meta['baseline_export_sha256']),
                           (ROOT / 'data/glossary-en.qj', seed_meta['packed_glossary_sha256']),
                           (DATA / 'english-tags.tsv', meta['sha256'])]:
        if sha(path) != expected:
            raise ValueError('Input checksum mismatch: ' + str(path))
    source_record = next(r for r in meta['input_files'] if r['path'] == 'ecdict.csv')
    source = ROOT / 'build/vocabulary-research/skywind3000__ECDICT/ecdict.csv'
    if sha(source) != source_record['sha256']:
        raise ValueError('ECDICT checksum mismatch')
    base = load_base(baseline)
    tags = {w: int(a) | int(b) for w, a, b in
            (row.split('\t') for row in (DATA / 'english-tags.tsv').read_text(encoding='utf-8').splitlines())}
    seed_rows = [tuple(row.split('\t')) for row in seed.read_text(encoding='utf-8').splitlines()]
    retained = collections.defaultdict(list)
    for row in seed_rows:
        retained[row[0]].append(row)
    original_words = {w for senses in base.values() for w, _ in senses}
    before_words = original_words | {row[1] for row in seed_rows}
    candidates = collections.defaultdict(dict)
    attempts = collections.defaultdict(collections.Counter)
    definitions = {}
    rejected = collections.Counter()
    manual_rejected = []
    guard = WordNetGuard()

    def add(chinese, english, pos, rank, origin):
        reason = None
        if (chinese, english) in REJECT_PAIRS:
            reason = 'known_ambiguous_pair'
        elif chinese not in base:
            reason = 'no_existing_chinese_key'
        elif not (tags.get(english, 0) & 3):
            reason = 'outside_cet4_cet6'
        elif not WORD.fullmatch(english) or pos not in set(POS.values()):
            reason = 'invalid_headword_or_pos'
        elif any(w == english for w, _ in base[chinese]) or any(row[1] == english for row in retained[chinese]):
            reason = 'already_mapped_for_key'
        elif origin == 'ECDICT' and pos not in {p for _, p in base[chinese]}:
            reason = 'pos_needs_review'
        elif origin == 'ECDICT' and not guard.related(english, pos, base[chinese]):
            reason = 'synonym_needs_review'
        if reason:
            rejected[reason] += 1
            attempts[english][reason] += 1
            if origin == 'Wordtrail-reviewed':
                manual_rejected.append(dict(chinese=chinese, word=english, pos=pos, reason=reason))
            return
        entry = (rank, pos, origin)
        old = candidates[chinese].get(english)
        if old is None or entry[0] < old[0]:
            candidates[chinese][english] = entry

    with source.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            english = row['word'].strip()
            if not (tags.get(english, 0) & 3) or english != english.lower():
                continue
            definitions[english] = row['translation']
            rank = int(row.get('frq') or row.get('bnc') or 999999) or 999999
            for chinese, pos in atomic_glosses(row['translation'], base):
                add(chinese, english, pos, rank, 'ECDICT')
    reviewed = BATCH / '01-reviewed.tsv'
    for line in reviewed.read_text(encoding='utf-8').splitlines():
        if line and not line.startswith('#'):
            chinese, english, pos = line.split('\t')
            add(chinese, english, pos, 0, 'Wordtrail-reviewed')

    rows = []
    additions = []
    for chinese in sorted(set(retained) | set(candidates)):
        kept = list(retained[chinese])
        # 在固定容量内先补之前整个词库没有的词；既有扩词不删不改顺序。
        choices = sorted(candidates[chinese].items(),
                         key=lambda item: (item[1][0] != 0, item[0] in before_words, item[1][0], item[0]))
        for english, (_, pos, origin) in choices:
            if len(kept) >= LIMIT:
                attempts[english]['per_key_capacity'] += 1
                rejected['per_key_capacity'] += 1
                continue
            row = (chinese, english, pos, origin)
            kept.append(row)
            additions.append(row)
        rows.extend(kept)
    payload = ''.join('\t'.join(row) + '\n' for row in rows).encode('utf-8')
    new_payload = ''.join('\t'.join(row) + '\n' for row in additions).encode('utf-8')
    all_extra = {row[1] for row in rows}
    after_words = original_words | all_extra
    # 这里只统计读音资源中有完整词面的条目，不合成缺失读音。
    ipa = set()
    for name in ('en_UK.txt', 'en_US.txt'):
        for line in (ROOT / 'pronunciation/source' / name).read_text(encoding='utf-8').splitlines():
            if '\t' in line:
                ipa.add(line.split('\t', 1)[0].strip().lower())
    pending = []
    for english, mask in sorted(tags.items()):
        if mask & 3 and english not in after_words:
            reasons = dict(sorted(attempts[english].items()))
            if not WORD.fullmatch(english):
                reasons['phrase_or_noncanonical_headword'] = 1
            if english not in definitions:
                reasons['not_in_pinned_ecdict_lowercase'] = 1
            if not reasons:
                reasons['no_atomic_supported_pos_gloss'] = 1
            pending.append(dict(word=english, targets=[code for bit, code in enumerate(('cet4', 'cet6')) if mask & (1 << bit)],
                                reasons=reasons, source_translation=definitions.get(english)))
    stats = dict(seed_meta)
    stats.update(version=2, batch='01-cet4-cet6', seed=dict(path='batches/00-expansion.tsv', sha256=sha(seed)),
                 reviewed_pairs_sha256=sha(reviewed), chinese_entries_extended=len({r[0] for r in rows}),
                 added_translation_pairs=len(rows), added_headwords=len(all_extra),
                 headwords_not_anywhere_in_original_glossary=len(all_extra - original_words),
                 bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest(),
                 by_target={t['id']: sum(bool(tags[r[1]] & (1 << i)) for r in rows) for i, t in enumerate(meta['tags'])},
                 reviewed_pairs_shipped=sum(r[3].startswith('Wordtrail-reviewed') for r in rows),
                 rules='Retain all batch00 pairs/order; batch01 scans all complete 2-6 CJK glosses per POS for CET4/CET6 only, exact Chinese key, compatible POS and WordNet synonym relation. Reviewed pairs explicitly allow Chinese noun/verb/adjective senses missing in the baseline. No substrings/parenthesis stripping/stemming; at most 8 additions per Chinese key.',
                 rejected=dict(rejected), batch01=dict(added_pairs=len(additions), involved_headwords=len({r[1] for r in additions}),
                    newly_mapped_headwords=len(after_words - before_words), entirely_new_headwords=len(after_words - before_words),
                    added_mapping_headwords_absent_from_original=len({r[1] for r in additions} - original_words),
                    reviewed_pairs=sum(r[3] == 'Wordtrail-reviewed' for r in additions),
                    reviewed_input_sha256=sha(reviewed), additions_sha256=hashlib.sha256(new_payload).hexdigest(),
                    manual_rejected=manual_rejected),
                 coverage_before=coverage(tags, before_words, ipa), coverage_after=coverage(tags, after_words, ipa),
                 coverage_scope='Distinct exact English headwords in fixed community exam lists with at least one Chinese glossary mapping. Not a claim that every mapped Chinese key is reachable in current pinyin candidates. IPA means at least one existing pronunciation resource.',
                 pending_distinct_cet_headwords=len(pending))
    pending_payload = (json.dumps(dict(batch='01', scope=stats['coverage_scope'], words=pending), ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    return {DATA / 'english-expansion.tsv': payload,
            BATCH / '01-additions.tsv': new_payload,
            DATA / 'expansion-manifest.json': (json.dumps(stats, ensure_ascii=False, indent=2) + '\n').encode('utf-8'),
            BATCH / '01-pending.json': pending_payload}, stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='只比较确定性重建结果，不写文件')
    args = parser.parse_args()
    outputs, stats = make_batch()
    for path, payload in outputs.items():
        if args.check:
            if not path.is_file() or path.read_bytes() != payload:
                raise ValueError('Regeneration differs: ' + str(path))
        else:
            path.write_bytes(payload)
    print(json.dumps({key: stats[key] for key in ['batch01', 'added_translation_pairs', 'bytes', 'coverage_before', 'coverage_after', 'pending_distinct_cet_headwords']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
