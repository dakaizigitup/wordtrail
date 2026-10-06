"""Audit exact 7–12 Han-character exam glosses against actual pinyin surfaces.

This is a review-only extension of batch02's short-gloss audit. It never
modifies shipped data and never extracts substrings from a longer definition.
Every emitted row requires exact same-headword, same-gloss, same-POS evidence
in both pinned sources.
"""
from pathlib import Path
import collections
import csv
import json
import re

from prepare_candidate_batch import (
    BATCH, DATA, KYLE_FILES, KYLE_POS, ROOT, load_sources, sha,
)
from prepare_cet_batch import load_base, LIMIT
from prepare_candidate_batch import PINNED_QJ_SHA256
from wordnet_guard import WordNetGuard

HAN_PHRASE = re.compile(r'[\u4e00-\u9fff]{7,12}')
POS_GLOSS = re.compile(r'^([a-z]+)\.\s*(.+)$')


def split_phrase_glosses(translation):
    for gloss in re.split('[,，;；、|]', str(translation)):
        chinese = gloss.strip()
        if HAN_PHRASE.fullmatch(chinese):
            yield chinese


def source_glosses(translation, pos_map):
    for line in str(translation).replace('\\n', '\n').splitlines():
        match = POS_GLOSS.match(line.strip())
        if not match or match[1] not in pos_map:
            continue
        for chinese in split_phrase_glosses(match[1] + '. ' + match[2]):
            yield chinese, pos_map[match[1]]


def main():
    meta, ecdict_record, ecdict, kyle_base, tags_path, pinyin_path = load_sources()
    if sha(DATA / 'english-tags.tsv') != meta['sha256']:
        raise ValueError('Pinned exam tag input checksum mismatch')
    if sha((DATA.parent.parent / 'data/dict.qj')) != PINNED_QJ_SHA256:
        raise ValueError('Pinned pinyin dictionary checksum mismatch')

    pending = {row['word'] for row in
               json.loads((BATCH / '02-pending.json').read_text(encoding='utf-8'))['words']}
    tags = {word: int(cet4) | int(cet6) for word, cet4, cet6 in
            (line.split('\t') for line in tags_path.read_text(encoding='utf-8').splitlines())}
    pinyin = {}
    for line in pinyin_path.read_text(encoding='utf-8').splitlines():
        chinese, code, frequency = line.split('\t')
        pinyin[chinese] = (code, int(frequency))

    kyle = collections.defaultdict(set)
    for filename in KYLE_FILES:
        with (kyle_base / filename).open(encoding='utf-8') as stream:
            for line in stream:
                row = json.loads(line)
                word = row.get('word', '').strip()
                if word not in pending or word != word.lower():
                    continue
                for meaning in row.get('translations', []):
                    source_pos = str(meaning.get('type', '')).strip().lower()
                    pos = KYLE_POS.get(source_pos)
                    if not pos:
                        continue
                    for chinese in split_phrase_glosses(meaning.get('translation', '')):
                        kyle[(word, chinese, pos)].add(filename.removesuffix('.jsonl'))

    ecdict_hits = {}
    ecdict_definitions = {}
    with ecdict.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            word = row['word'].strip()
            if word not in pending or word != word.lower():
                continue
            ecdict_definitions[word] = row['translation']
            for chinese, pos in source_glosses(row['translation'], {
                'n': 'n.', 'noun': 'n.', 'v': 'v.', 'verb': 'v.', 'vt': 'v.', 'vi': 'v.',
                'a': 'adj.', 'adj': 'adj.', 'adjective': 'adj.', 'adv': 'adv.', 'adverb': 'adv.',
            }):
                ecdict_hits[(word, chinese, pos)] = row.get('frq') or row.get('bnc') or '999999'

    base = load_base(ROOT / 'build/expansion-base.tsv')
    extra = collections.defaultdict(list)
    for line in (DATA / 'english-expansion.tsv').read_text(encoding='utf-8').splitlines():
        chinese, word, pos, source = line.split('\t')
        extra[chinese].append((word, pos, source))

    guard = WordNetGuard()
    rows = []
    decisions = collections.Counter()
    for (word, chinese, pos), kyle_sources in sorted(kyle.items()):
        if (word, chinese, pos) not in ecdict_hits:
            continue
        if chinese not in pinyin:
            decision = 'not_a_pinyin_candidate'
            code, frequency = '', 0
        elif chinese not in base:
            decision = 'new_chinese_key_requires_manual_review'
            code, frequency = pinyin[chinese]
        elif pos not in {base_pos for _, base_pos in base[chinese]}:
            decision = 'base_pos_mismatch_requires_manual_review'
            code, frequency = pinyin[chinese]
        elif any(existing_word == word for existing_word, _, _ in extra[chinese]):
            decision = 'already_mapped_for_key'
            code, frequency = pinyin[chinese]
        elif not guard.synsets(word, pos):
            decision = 'wordnet_lemma_pos_missing'
            code, frequency = pinyin[chinese]
        elif not guard.related(word, pos, base[chinese]):
            decision = 'wordnet_not_related_to_existing_gloss'
            code, frequency = pinyin[chinese]
        elif len(extra[chinese]) >= LIMIT:
            decision = 'per_key_capacity'
            code, frequency = pinyin[chinese]
        else:
            decision = 'eligible'
            code, frequency = pinyin[chinese]
        decisions[decision] += 1
        exam_targets = ','.join(code for bit, code in enumerate(('cet4', 'cet6'))
                                if tags.get(word, 0) & (1 << bit))
        try:
            rank = int(ecdict_hits[(word, chinese, pos)])
        except ValueError:
            rank = 999999
        rows.append((decision, word, chinese, pos, exam_targets,
                     ','.join(sorted(kyle_sources)), code, str(frequency), str(rank),
                     ','.join(sorted({p for _, p in base.get(chinese, [])})),
                     ecdict_definitions.get(word, '').replace('\n', r'\n')))
    rows.sort(key=lambda row: (row[0] != 'eligible', -int(row[7] or 0), int(row[8]), row[1], row[2]))
    output = Path(__file__).resolve().parents[1] / 'build'
    output.mkdir(exist_ok=True)
    header = ('decision\tword\tchinese\tpos\texam_targets\texact_kyle_sources\t'
              'pinyin\tpinyin_frequency\tecdict_rank\tbase_pos\tecdict_translation\n')
    (output / 'batch02-long-gloss-evidence.tsv').write_text(
        header + ''.join('\t'.join(row) + '\n' for row in rows), encoding='utf-8', newline='\n')
    report = {
        'batch': '02', 'scope': 'Exact complete 7–12 Han-character glosses only; no substrings.',
        'pending_cet_headwords': len(pending), 'cross_source_pairs': len(rows),
        'cross_source_unique_headwords': len({row[1] for row in rows}),
        'reachable_pairs': sum(row[0] != 'not_a_pinyin_candidate' for row in rows),
        'decisions': dict(sorted(decisions.items())),
        'ecdict_sha256': ecdict_record['sha256'], 'pinyin_candidates_sha256': sha(pinyin_path),
        'rule': 'Require exact same headword, whole Chinese phrase and POS in fixed ECDICT and both fixed CET source files; then separately assess exact pinyin candidate, base POS, WordNet relation and key capacity. Review-only; does not change shipped data.'
    }
    (output / 'batch02-long-gloss-summary.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
