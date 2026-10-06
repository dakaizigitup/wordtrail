"""Propose reachable second-stage CET mappings without modifying shipped data.

The output is a review queue: every proposed Chinese gloss is an exact short
ECDICT gloss present in the pinned pinyin candidates. Existing Chinese keys
are additionally checked for POS compatibility and a WordNet relation to the
packed Qingjian senses. Novel Chinese keys are kept separate for manual review.
"""
from pathlib import Path
import collections
import csv
import json

from prepare_candidate_batch import (
    ROOT, DATA, BATCH, KYLE_FILES, KYLE_POS, kyle_glosses, load_sources,
    parse_pinyin_candidates, source_pos_glosses, sha,
)
from prepare_cet_batch import load_base
from wordnet_guard import WordNetGuard


def main():
    meta, ecdict_record, ecdict, kyle_base, tags_path, pinyin_path = load_sources()
    batch = json.loads((BATCH / '02-pending.json').read_text(encoding='utf-8'))
    missing = {row['word'] for row in batch['words']}
    tags = {word: int(cet4) | int(cet6) for word, cet4, cet6 in
            (line.split('\t') for line in tags_path.read_text(encoding='utf-8').splitlines())}
    pinyin = parse_pinyin_candidates(pinyin_path)
    base = load_base(ROOT / 'build/expansion-base.tsv')
    current = collections.defaultdict(set)
    for line in (DATA / 'english-expansion.tsv').read_text(encoding='utf-8').splitlines():
        chinese, word, pos, _source = line.split('\t')
        current[chinese].add(word)
    kyle = collections.defaultdict(set)
    kyle_translations = collections.defaultdict(set)
    for filename in KYLE_FILES:
        with (kyle_base / filename).open(encoding='utf-8') as stream:
            for line in stream:
                row = json.loads(line)
                word = row.get('word', '').strip()
                if word not in missing or word != word.lower():
                    continue
                for meaning in row.get('translations', []):
                    pos = KYLE_POS.get(str(meaning.get('type', '')).strip().lower())
                    raw_translation = str(meaning.get('translation', '')).strip()
                    if pos and raw_translation:
                        kyle[(word, pos)].add(raw_translation)
                        for chinese in kyle_glosses(raw_translation):
                            kyle_translations[(word, chinese, pos)].add(filename.removesuffix('.jsonl'))

    guard = WordNetGuard()
    proposed = []
    novel = []
    seen_ecdict = set()
    with ecdict.open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            word = row['word'].strip()
            if word not in missing or word != word.lower():
                continue
            try:
                frequency = int(row.get('frq') or row.get('bnc') or 999999) or 999999
            except ValueError:
                frequency = 999999
            for chinese, pos in source_pos_glosses(row['translation']):
                if chinese not in pinyin or (word, chinese, pos) in seen_ecdict:
                    continue
                seen_ecdict.add((word, chinese, pos))
                if word in current[chinese]:
                    continue
                kyle_same_pos = sorted(kyle[(word, pos)])
                exam = ','.join(code for bit, code in enumerate(('cet4', 'cet6')) if tags[word] & (1 << bit))
                if chinese not in base:
                    exact_kyle = kyle_translations.get((word, chinese, pos), set())
                    novel.append((word, chinese, pos, exam, ','.join(sorted(exact_kyle)),
                                  pinyin[chinese][0], str(pinyin[chinese][1]),
                                  str(frequency), '|'.join(kyle_same_pos), row['translation'].replace('\n', r'\n')))
                    continue
                base_pos = sorted({sense_pos for _, sense_pos in base[chinese]})
                if pos not in base_pos:
                    continue
                if not guard.synsets(word, pos) or not guard.related(word, pos, base[chinese]):
                    continue
                exact_kyle = kyle_translations.get((word, chinese, pos), set())
                proposed.append((word, chinese, pos, exam, ','.join(sorted(exact_kyle)),
                                 '|'.join(kyle_same_pos), pinyin[chinese][0], str(pinyin[chinese][1]),
                                 str(frequency), ','.join(base_pos), row['translation'].replace('\n', r'\n')))

    proposed.sort(key=lambda r: (-int(r[7]), int(r[8]), r[0], r[1]))
    novel.sort(key=lambda r: (-int(r[6]), int(r[7]), r[0], r[1]))
    output = ROOT / 'build'
    output.mkdir(exist_ok=True)
    header = 'word\tchinese\tpos\texam_targets\texact_kyle_sources\tkyle_same_pos_glosses\tpinyin\tpinyin_frequency\tecdict_rank\tbase_pos\tecdict_translation\n'
    (output / 'batch02-semantic-candidates.tsv').write_text(
        header + ''.join('\t'.join(row) + '\n' for row in proposed), encoding='utf-8')
    novel_header = 'word\tchinese\tpos\texam_targets\texact_kyle_sources\tpinyin\tpinyin_frequency\tecdict_rank\tkyle_same_pos_glosses\tecdict_translation\n'
    (output / 'batch02-new-key-candidates.tsv').write_text(
        novel_header + ''.join('\t'.join(row) + '\n' for row in novel), encoding='utf-8')
    report = {
        'pending_cet_headwords': len(missing),
        'reachable_existing_key_word_pos_pairs': len(proposed),
        'reachable_existing_key_unique_words': len({row[0] for row in proposed}),
        'same_english_chinese_pos_in_kyle': sum(bool(row[4]) for row in proposed),
        'reachable_novel_chinese_keys': len(novel),
        'novel_key_unique_words': len({row[0] for row in novel}),
        'ecdict_sha256': ecdict_record['sha256'],
        'pinyin_candidates_sha256': sha(pinyin_path),
        'source_rule': 'ECDICT exact short gloss + exact current pinyin candidate; existing-key proposals also need matching POS and WordNet lemma/synset relation. Novel Chinese keys need manual semantic review.',
    }
    (output / 'batch02-gap-analysis.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
