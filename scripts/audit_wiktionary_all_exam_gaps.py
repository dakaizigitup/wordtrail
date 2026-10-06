"""Create a review-only queue from the pinned Mandarin Wiktionary snapshot.

The script never changes shipped data. It proposes only exact Chinese-key /
English-headword matches with a supported English part of speech, a pinned
exam tag, an existing pinyin candidate, and bundled IPA.
"""
from __future__ import annotations

import collections
import csv
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_wiktionary_expansion import DATA, exam_inputs, read_expansion
from prepare_candidate_batch import source_pos_glosses
from prepare_cet_batch import load_base
from exam_targets import load_exam_tags, RUNTIME_EXPANSIONS


SNAPSHOT_DIR = ROOT / "build/source-audit/kaikki-zh-english-2026.09.09"
DATABASE = SNAPSHOT_DIR / "lexhint-zh-english-dictionary-s10-2026.09.09.sqlite3"
EXPECTED_DATABASE_SHA256 = "98fef9ba82047d0eaba650c1da074810c135da3c90e1fdb59f2faf197d6b7dd2"
OUTPUT = SNAPSHOT_DIR / "exam-review-candidates.tsv"
SUMMARY = SNAPSHOT_DIR / "exam-review-summary.json"
TARGETS = ("cet4", "cet6", "tem4", "tem8", "toefl", "ielts")
POS = {"noun": "n.", "verb": "v.", "adj": "adj.", "adv": "adv."}
WORD = re.compile(r"[a-z]+(?:[-'][a-z]+)*\Z")
MAX_EXTRA_PER_KEY = 8


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if not DATABASE.is_file() or sha(DATABASE) != EXPECTED_DATABASE_SHA256:
        raise SystemExit("Missing or changed pinned Kaikki-derived snapshot: " + str(DATABASE))

    tags = load_exam_tags(DATA)
    candidate_pinyin = {}
    pinyin_path = ROOT / "build/pinyin-candidates.tsv"
    for line in pinyin_path.read_text(encoding="utf-8").splitlines():
        chinese, pinyin, frequency = line.split("\t")
        candidate_pinyin[chinese] = (pinyin, int(frequency))
    _, _, ipa = exam_inputs()

    base = load_base(ROOT / "build/expansion-base.tsv")
    existing_words = {word for senses in base.values() for word, _ in senses}
    extra_by_key: dict[str, list[str]] = collections.defaultdict(list)
    runtime_names = RUNTIME_EXPANSIONS
    for name in runtime_names:
        for row in read_expansion(DATA / name):
            extra_by_key[row["chinese"]].append(row["english"])
            existing_words.add(row["english"])

    missing = {word for word, mask in tags.items() if mask and word not in existing_words}
    ecdict_path = ROOT / "build/vocabulary-research/skywind3000__ECDICT/ecdict.csv"
    source_pos = collections.defaultdict(set)
    with ecdict_path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            word = row["word"].strip().casefold()
            if word in missing:
                source_pos[word].update(pos for _, pos in source_pos_glosses(row["translation"]))

    candidates = {}
    connection = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True)
    try:
        query = """SELECT e.id, e.word, e.pos, s.id, s.glosses
                   FROM entries e JOIN senses s ON s.entry_id=e.id"""
        for entry_id, chinese, source_part, sense_id, raw_glosses in connection.execute(query):
            english_pos = POS.get(source_part)
            if not english_pos or chinese not in candidate_pinyin:
                continue
            for gloss in json.loads(raw_glosses):
                headword = gloss.strip().casefold()
                if headword.startswith("to "):
                    headword = headword[3:].strip()
                if (headword not in missing or english_pos not in source_pos[headword]
                        or headword not in ipa or not WORD.fullmatch(headword)):
                    continue
                mask = tags[headword]
                targets = [target for bit, target in enumerate(TARGETS) if mask & (1 << bit)]
                pinyin, frequency = candidate_pinyin[chinese]
                key = (headword, chinese, english_pos, gloss)
                candidates[key] = {
                    "word": headword,
                    "chinese": chinese,
                    "pos": english_pos,
                    "source_pos": source_part,
                    "source_gloss": gloss,
                    "targets": ",".join(targets),
                    "mask": str(mask),
                    "pinyin": pinyin,
                    "pinyin_frequency": str(frequency),
                    "ipa": "yes",
                    "extra_count": str(len(extra_by_key.get(chinese, []))),
                    "key_capacity": "available" if len(extra_by_key.get(chinese, [])) < MAX_EXTRA_PER_KEY else "full",
                    "snapshot_entry_id": str(entry_id),
                    "snapshot_sense_id": str(sense_id),
                }
    finally:
        connection.close()

    headers = (
        "word", "chinese", "pos", "source_pos", "source_gloss", "targets", "mask",
        "pinyin", "pinyin_frequency", "ipa", "extra_count", "key_capacity",
        "snapshot_entry_id", "snapshot_sense_id",
    )
    ordered = sorted(candidates.values(), key=lambda row: (
        -len(row["targets"].split(",")), -int(row["pinyin_frequency"]), row["word"], row["chinese"],
    ))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(ordered)

    summary = {
        "scope": "all six pinned community exam-tag sources",
        "fixed_snapshot": DATABASE.name,
        "snapshot_sha256": sha(DATABASE),
        "pinyin_candidates_sha256": sha(pinyin_path),
        "exam_tag_index_sha256": sha(DATA / "english-tags.tsv"),
        "openetymology_tag_index_sha256": sha(DATA / "openetymology-exam-tags.tsv"),
        "ecdict_sha256": sha(ecdict_path),
        "english_uk_ipa_sha256": sha(ROOT / "pronunciation/source/en_UK.txt"),
        "english_us_ipa_sha256": sha(ROOT / "pronunciation/source/en_US.txt"),
        "missing_unique_headwords_before_review": len(missing),
        "exact_candidates_after_pos_pinyin_ipa_filters": len(ordered),
        "candidate_headwords": len({row["word"] for row in ordered}),
        "candidate_headwords_by_target": {
            target: len({row["word"] for row in ordered if target in row["targets"].split(",")})
            for target in TARGETS
        },
        "output_sha256": sha(OUTPUT),
        "caveat": "Automated candidates are not approved mappings. Homographs, register, domain labels, and sense compatibility still need row-level review against pinned Wiktionary revisions.",
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
