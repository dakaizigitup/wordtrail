"""Audit and conservatively add reachable CET4/CET6 mappings for batch 02.

Only exact Chinese glosses shared by the pinned exam wordlist and ECDICT are
considered. Automatic additions also require an existing pinyin candidate,
matching source/base parts of speech, a WordNet relation to the packed glossary,
and a free expansion slot. Explicitly reviewed pairs can resolve a Chinese-POS
variant or a missed WordNet relation, but still need exact two-source evidence
and a real pinyin candidate.
"""
from pathlib import Path
import argparse
import collections
import csv
import hashlib
import json
import re

from prepare_cet_batch import ROOT, DATA, BATCH, LIMIT, WORD, load_base, coverage
from prepare_expansion import POS
from wordnet_guard import WordNetGuard

KYLE_FILES = {
    '四级.jsonl': 'd099f10a9faaeaf694c332ad7aa73648a777af01dbc2f6f4088cae52906a5649',
    '六级.jsonl': 'e902347a69724f420b970f89c94f64a82bb03c2128347fc1f775fa2f87a060e2',
}
PINNED_QJ_SHA256 = '3e33b16a84df555e6f16d52ac8ab3c2c6b6f1f71734e69463861fd5abd9c19dc'
PINNED_BATCH01_EXPANSION_SHA256 = '8ce49a7d511601d1ac337c689541b95b7bbce08c013ea0bc0e859be5337955c4'
KYLE_POS = {
    'n': 'n.', 'noun': 'n.',
    'v': 'v.', 'verb': 'v.', 'vt': 'v.', 'vi': 'v.',
    'a': 'adj.', 'adj': 'adj.', 'adjective': 'adj.',
    'adv': 'adv.', 'adverb': 'adv.',
}
HAN = re.compile(r'[\u4e00-\u9fff]{2,6}')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_pos_glosses(translation):
    """Yield only complete, short, POS-marked Chinese glosses; no slicing."""
    for line in translation.replace('\\n', '\n').splitlines():
        match = re.match(r'^([a-z]+)\.\s*(.+)$', line.strip())
        if not match or match[1] not in POS:
            continue
        pos = POS[match[1]]
        for gloss in re.split('[,，;；]', match[2]):
            chinese = gloss.strip()
            if HAN.fullmatch(chinese):
                yield chinese, pos


def parse_pinyin_candidates(path):
    result = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        chinese, pinyin, frequency = line.split('\t')
        if HAN.fullmatch(chinese):
            result[chinese] = (pinyin, int(frequency))
    return result


def load_sources():
    meta = json.loads((DATA / 'manifest.json').read_text(encoding='utf-8'))
    records = {row['path']: row for row in meta['input_files']}
    ecdict_record = records['ecdict.csv']
    ecdict = ROOT / 'build/vocabulary-research/skywind3000__ECDICT/ecdict.csv'
    if sha(ecdict) != ecdict_record['sha256']:
        raise ValueError('Pinned ECDICT checksum mismatch')
    kyle_base = ROOT / 'build/vocabulary-research/KyleBing__english-vocabulary/full_line_jsonl/simple/正序'
    for filename, expected in KYLE_FILES.items():
        actual = kyle_base / filename
        if sha(actual) != expected or records['full_line_jsonl/simple/正序/' + filename]['sha256'] != expected:
            raise ValueError('Pinned KyleBing checksum mismatch: ' + filename)
    tags_path = DATA / 'english-tags.tsv'
    if sha(tags_path) != meta['sha256']:
        raise ValueError('Exam tag input checksum mismatch')
    pinyin_path = ROOT / 'build/pinyin-candidates.tsv'
    if sha(ROOT / 'data/dict.qj') != PINNED_QJ_SHA256:
        raise ValueError('Pinned pinyin dictionary checksum mismatch')
    if not pinyin_path.is_file():
        raise ValueError('Run export_pinyin_candidates first')
    return meta, ecdict_record, ecdict, kyle_base, tags_path, pinyin_path


def make_batch(apply=False, check=False):
    meta, ecdict_record, ecdict, kyle_base, tags_path, pinyin_path = load_sources()
    seed_meta = json.loads((DATA / 'expansion-manifest.json').read_text(encoding='utf-8'))
    baseline = ROOT / 'build/expansion-base.tsv'
    if sha(baseline) != seed_meta['baseline_export_sha256']:
        raise ValueError('Actual packed glossary export checksum mismatch')
    if sha(ROOT / 'data/glossary-en.qj') != seed_meta['packed_glossary_sha256']:
        raise ValueError('Packed glossary checksum mismatch')
    previous = BATCH / '01-expansion.tsv'
    if previous.is_file():
        if sha(previous) != PINNED_BATCH01_EXPANSION_SHA256:
            raise ValueError('Pinned batch01 expansion snapshot checksum mismatch')
    else:
        previous = DATA / 'english-expansion.tsv'
        if sha(previous) != PINNED_BATCH01_EXPANSION_SHA256:
            raise ValueError('Batch01 expansion checksum mismatch; expected the published batch01 input')
    base = load_base(baseline)
    tags = {w: int(a) | int(b) for w, a, b in
            (row.split('\t') for row in tags_path.read_text(encoding='utf-8').splitlines())}
    current_rows = [tuple(line.split('\t')) for line in previous.read_text(encoding='utf-8').splitlines()]
    current_extra = collections.defaultdict(list)
    for row in current_rows:
        current_extra[row[0]].append(row)
    original_words = {word for senses in base.values() for word, _ in senses}
    current_words = original_words | {row[1] for row in current_rows}
    pending = {word for word, mask in tags.items() if mask & 3 and word not in current_words}
    pinyin = parse_pinyin_candidates(pinyin_path)

    # Store source evidence at the exact (English, Chinese, POS) granularity.
    kyle = collections.defaultdict(set)
    for filename in KYLE_FILES:
        with (kyle_base / filename).open(encoding='utf-8') as stream:
            for line in stream:
                row = json.loads(line)
                word = row.get('word', '').strip()
                if word not in pending or word != word.lower():
                    continue
                for meaning in row.get('translations', []):
                    pos = KYLE_POS.get(str(meaning.get('type', '')).strip().lower())
                    chinese = str(meaning.get('translation', '')).strip()
                    if pos and HAN.fullmatch(chinese):
                        kyle[(word, chinese, pos)].add(filename.removesuffix('.jsonl'))

    ecdict_hits = collections.defaultdict(lambda: 999999)
    definitions = {}
    with ecdict.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            word = row['word'].strip()
            if word not in pending or word != word.lower():
                continue
            definitions[word] = row['translation']
            try:
                rank = int(row.get('frq') or row.get('bnc') or 999999) or 999999
            except ValueError:
                rank = 999999
            for chinese, pos in source_pos_glosses(row['translation']):
                ecdict_hits[(word, chinese, pos)] = min(ecdict_hits[(word, chinese, pos)], rank)

    guard = WordNetGuard()
    reviewed_path = BATCH / '02-reviewed.tsv'
    manual = []
    for line in reviewed_path.read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        chinese, word, pos = line.split('\t')
        if word not in pending or chinese not in base or chinese not in pinyin:
            raise ValueError('Reviewed pair is not a missing word on an existing reachable key: ' + line)
        if pos not in {source_pos for (w, c, source_pos) in kyle if w == word and c == chinese} or (word, chinese, pos) not in ecdict_hits:
            raise ValueError('Reviewed pair lacks exact same-POS agreement in both pinned sources: ' + line)
        if any(old_word == word for old_word, _ in base[chinese]) or any(row[1] == word for row in current_extra[chinese]):
            raise ValueError('Reviewed pair is already mapped: ' + line)
        manual.append((chinese, word, pos))
    if len(set(manual)) != len(manual):
        raise ValueError('Duplicate reviewed pair')

    evidence_rows = []
    eligible = collections.defaultdict(list)
    for (word, chinese, pos), files in sorted(kyle.items()):
        if (word, chinese, pos) not in ecdict_hits:
            continue
        reason = 'eligible'
        if chinese not in pinyin:
            reason = 'not_a_pinyin_candidate'
        elif chinese not in base:
            reason = 'new_chinese_key_requires_manual_review'
        elif pos not in {base_pos for _, base_pos in base[chinese]}:
            reason = 'base_pos_mismatch'
        elif any(old_word == word for old_word, _ in base[chinese]) or any(row[1] == word for row in current_extra[chinese]):
            reason = 'already_mapped_for_key'
        elif (chinese, word) in {('丰富', 'affluent')}:
            reason = 'known_ambiguous_pair'
        elif not guard.synsets(word, pos):
            reason = 'wordnet_lemma_pos_missing'
        elif not guard.related(word, pos, base[chinese]):
            reason = 'wordnet_not_related_to_existing_gloss'
        elif len(current_extra[chinese]) >= LIMIT:
            reason = 'per_key_capacity'
        pinyin_value, frequency = pinyin.get(chinese, ('', 0))
        base_pos = ','.join(sorted({p for _, p in base.get(chinese, [])}))
        exam_mask = tags.get(word, 0)
        if (chinese, word, pos) in manual:
            reason = 'manual_reviewed_pos_or_semantic_variant'
        evidence_rows.append((word, chinese, pos, ','.join(sorted(files)), str(exam_mask),
                              str(ecdict_hits[(word, chinese, pos)]), pinyin_value,
                              str(frequency), base_pos, reason))
        if reason == 'eligible':
            eligible[chinese].append((word, pos, ecdict_hits[(word, chinese, pos)], frequency, ','.join(sorted(files))))

    # Preserve existing records, then reviewed items, then automatic items, all within 8 per key.
    additions = []
    remaining = collections.Counter({chinese: LIMIT - len(rows) for chinese, rows in current_extra.items()})
    manual_rows = []
    for chinese, word, pos in manual:
        remaining[chinese] = LIMIT - len(current_extra[chinese]) if chinese not in remaining else remaining[chinese]
        if remaining[chinese] <= 0:
            raise ValueError('Reviewed pairs exceed per-key capacity: ' + chinese)
        manual_rows.append((chinese, word, pos, 'Wordtrail-batch02-reviewed'))
        remaining[chinese] -= 1
    additions.extend(manual_rows)
    for chinese in sorted(eligible):
        slots = remaining[chinese] if chinese in remaining else LIMIT - len(current_extra[chinese])
        choices = sorted(eligible[chinese], key=lambda r: (-r[3], r[2], r[0], r[1]))
        for word, pos, rank, frequency, files in choices[:slots]:
            additions.append((chinese, word, pos, 'Wordtrail-batch02'))
            remaining[chinese] -= 1

    final_rows = current_rows + additions
    final_payload = ''.join('\t'.join(row) + '\n' for row in final_rows).encode('utf-8')
    additions_payload = ''.join('\t'.join(row) + '\n' for row in additions).encode('utf-8')
    audit_payload = ('word\tchinese\tpos\texam_sources\texam_tag_mask\tecdict_frequency_rank\tpinyin\tpinyin_frequency\tbase_pos\tdecision\n' +
                     ''.join('\t'.join(row) + '\n' for row in evidence_rows)).encode('utf-8')
    after_words = current_words | {row[1] for row in additions}
    counts = collections.Counter(row[-1] for row in evidence_rows)
    selected = {(row[0], row[1], row[2]) for row in additions}
    for index, row in enumerate(evidence_rows):
        if row[-1] == 'eligible' and (row[1], row[0], row[2]) not in selected:
            evidence_rows[index] = (*row[:-1], 'deferred_per_key_capacity')
    counts = collections.Counter(row[-1] for row in evidence_rows)
    audit_payload = ('word\tchinese\tpos\texam_sources\texam_tag_mask\tecdict_frequency_rank\tpinyin\tpinyin_frequency\tbase_pos\tdecision\n' +
                     ''.join('\t'.join(row) + '\n' for row in evidence_rows)).encode('utf-8')
    ipa = set()
    for name in ('en_UK.txt', 'en_US.txt'):
        for line in (ROOT / 'pronunciation/source' / name).read_text(encoding='utf-8').splitlines():
            if '\t' in line:
                ipa.add(line.split('\t', 1)[0].strip().lower())
    old_coverage = coverage(tags, current_words, ipa)
    new_coverage = coverage(tags, after_words, ipa)
    reachable_before = {word for chinese, senses in base.items() if chinese in pinyin
                        for word, _ in senses} | {row[1] for row in current_rows if row[0] in pinyin}
    reachable_after = reachable_before | {row[1] for row in additions}
    old_reachable_coverage = coverage(tags, reachable_before, ipa)
    new_reachable_coverage = coverage(tags, reachable_after, ipa)
    pending_rows = []
    candidate_reasons = collections.defaultdict(set)
    for row in evidence_rows:
        candidate_reasons[row[0]].add(row[-1])
    for word in sorted(tags):
        if tags[word] & 3 and word not in after_words:
            reasons = sorted(candidate_reasons.get(word, set()))
            if not reasons:
                reasons.append('no_exact_cross_source_gloss')
            pending_rows.append(dict(word=word,
                targets=[code for bit, code in enumerate(('cet4', 'cet6')) if tags[word] & (1 << bit)],
                candidate_reasons=reasons, ecdict_translation=definitions.get(word)))

    stats = dict(seed_batch01_sha256=sha(previous), pinyin_dictionary_sha256=PINNED_QJ_SHA256,
                 pinyin_candidates_sha256=sha(pinyin_path), kylebing_files=KYLE_FILES,
                 ecdict_sha256=ecdict_record['sha256'], evidence_pairs=len(evidence_rows),
                 evidence_words=len({row[0] for row in evidence_rows}),
                 decisions=dict(sorted(counts.items())), added_pairs=len(additions),
                 manual_reviewed_pairs=len(manual_rows), reviewed_input_sha256=sha(reviewed_path),
                 added_headwords=len({row[1] for row in additions}),
                 added_chinese_keys=len({row[0] for row in additions}),
                 added_headwords_not_in_original=len({row[1] for row in additions} - original_words),
                 additions_sha256=hashlib.sha256(additions_payload).hexdigest(),
                 expansion_bytes=len(final_payload), expansion_sha256=hashlib.sha256(final_payload).hexdigest(),
                 coverage_before=old_coverage, coverage_after=new_coverage,
                 candidate_reachable_coverage_before=old_reachable_coverage,
                 candidate_reachable_coverage_after=new_reachable_coverage,
                 pending_cet_headwords=len(pending_rows),
                 rules='Only exact short Chinese glosses shared by fixed CET4/CET6 KyleBing rows and pinned ECDICT. Automatic additions need an exact pinyin candidate, existing packed glossary key, matching base POS and WordNet lemma/synonym relation. Explicitly reviewed pairs may resolve a Chinese-POS or WordNet relation difference but retain source agreement and exact pinyin candidate requirements. Maximum 8 extras per key. New Chinese keys and phrases remain for later manual review. Chinese candidate ordering is unchanged.')
    pending_payload = (json.dumps(dict(batch='02', scope='Fixed community CET4/CET6 lists; exact headword mapping and pinyin-candidate reachability are reported separately.', words=pending_rows), ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    outputs = {
        ROOT / 'build/batch02-evidence.tsv': audit_payload,
        ROOT / 'build/batch02-summary.json': (json.dumps(stats, ensure_ascii=False, indent=2) + '\n').encode('utf-8'),
        DATA / 'batches/02-additions.tsv': additions_payload,
        DATA / 'batches/02-pending.json': pending_payload,
        DATA / 'english-expansion.tsv': final_payload,
    }
    if apply:
        outputs[BATCH / '01-expansion.tsv'] = previous.read_bytes()
        outputs[BATCH / '02-manifest.json'] = (json.dumps(stats, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        cumulative = dict(seed_meta)
        all_extra = {row[1] for row in final_rows}
        cumulative.update(
            batch02=stats,
            chinese_entries_extended=len({row[0] for row in final_rows}),
            added_translation_pairs=len(final_rows),
            added_headwords=len(all_extra),
            headwords_not_anywhere_in_original_glossary=len(all_extra - original_words),
            bytes=len(final_payload),
            sha256=hashlib.sha256(final_payload).hexdigest(),
            by_target={target['id']: sum(bool(tags[row[1]] & (1 << bit)) for row in final_rows)
                       for bit, target in enumerate(meta['tags'])},
            coverage_after=new_coverage,
            candidate_reachable_coverage_after=new_reachable_coverage,
            pending_distinct_cet_headwords=len(pending_rows),
            coverage_scope='Distinct exact English headwords in fixed community exam lists with at least one Chinese glossary mapping. Candidate reachability is counted separately when an exact Chinese key occurs in the pinned pinyin dictionary. Neither figure claims official completeness.'
        )
        outputs[DATA / 'expansion-manifest.json'] = (json.dumps(cumulative, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if not apply:
        outputs = {key: value for key, value in outputs.items() if 'build/' in key.as_posix()}
    for path, payload in outputs.items():
        if check:
            if not path.is_file() or path.read_bytes() != payload:
                raise ValueError('Regeneration differs: ' + str(path))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
    print(json.dumps({k: stats[k] for k in ['evidence_pairs', 'evidence_words', 'decisions', 'added_pairs', 'added_headwords', 'added_chinese_keys', 'coverage_before', 'coverage_after', 'pending_cet_headwords']}, ensure_ascii=False, indent=2))
    return outputs, stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='write batch02 additions and cumulative runtime glossary')
    parser.add_argument('--check', action='store_true', help='regenerate and compare outputs without writing')
    args = parser.parse_args()
    make_batch(apply=args.apply, check=args.check)


if __name__ == '__main__':
    main()
