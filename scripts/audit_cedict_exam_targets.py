"""Generate a review-only CC-CEDICT queue for missing TEM/TOEFL/IELTS words.

Only exact full English headword glosses (or ``to <headword>``) are matched.
The simplified Chinese entry must be an exact current Qingjian pinyin
candidate, but need not already have an English glossary entry: the runtime
expansion translator supports exact candidate keys with no base translation.
This script only produces an audit queue and never changes shipped data.
"""
from __future__ import annotations

import collections
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_cedict_cet_gaps import (  # pinned source and parsing definitions
    DEFAULT_SOURCE, ENTRY, HAN, PINNED_COMMIT, PINNED_PATH, PINNED_REPO,
    PINNED_SHA256, PINNED_URL, POS_MAP, load_ecdict, load_ipa, sha,
)
from prepare_cet_batch import load_base
from prepare_candidate_batch import parse_pinyin_candidates
from exam_targets import load_exam_tags, RUNTIME_EXPANSIONS

DATA = ROOT / "vocabulary/data"
OUT = ROOT / "build/source-audit/cc-cedict/exam-targets"
TARGETS = ("tem4", "tem8", "toefl", "ielts")
BIT = {target: bit for bit, target in enumerate(("cet4", "cet6", "tem4", "tem8", "toefl", "ielts"))}
RUNTIME_FILES = RUNTIME_EXPANSIONS


def main() -> None:
    source = DEFAULT_SOURCE
    if not source.is_file() or sha(source) != PINNED_SHA256:
        raise SystemExit("Missing or changed pinned CC-CEDICT snapshot: " + str(source))
    tag_path = DATA / "english-tags.tsv"
    tags = load_exam_tags(DATA)
    tag_manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    if sha(tag_path) != tag_manifest["sha256"]:
        raise SystemExit("Pinned exam tag index checksum mismatch")

    base = load_base(ROOT / "build/expansion-base.tsv")
    pinyin = parse_pinyin_candidates(ROOT / "build/pinyin-candidates.tsv")
    ipa = load_ipa()
    current_words = {word for senses in base.values() for word, _ in senses}
    current_rows_by_key: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    for filename in RUNTIME_FILES:
        for line in (DATA / filename).read_text(encoding="utf-8").splitlines():
            chinese, english, pos, _source = line.split("\t")
            current_words.add(english)
            current_rows_by_key[chinese].append((english, pos))

    missing_by_target = {
        target: {word for word, mask in tags.items()
                 if mask & (1 << BIT[target]) and word not in current_words}
        for target in TARGETS
    }
    missing_union = set().union(*missing_by_target.values())
    gloss_to_words: dict[str, set[str]] = collections.defaultdict(set)
    for word in missing_union:
        if word in ipa:
            gloss_to_words[word].add(word)
            gloss_to_words["to " + word].add(word)

    ecdict = load_ecdict()
    candidates: dict[tuple[str, str, str], dict[str, str]] = {}
    parsed_entries = 0
    for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        match = ENTRY.fullmatch(line)
        if not match:
            continue
        parsed_entries += 1
        traditional, simplified, cedict_pinyin, definitions = match.groups()
        if not HAN.fullmatch(simplified) or simplified not in pinyin:
            continue
        for definition in definitions.split("/"):
            gloss = definition.strip().casefold()
            for word in gloss_to_words.get(gloss, ()):
                word_tags = tags[word]
                target_tags = [name for bit, name in enumerate(("cet4", "cet6", "tem4", "tem8", "toefl", "ielts"))
                               if word_tags & (1 << bit)]
                row = {
                    "word": word,
                    "targets": ",".join(target_tags),
                    "pos": ecdict.get(word, {}).get("pos", ""),
                    "chinese": simplified,
                    "pinyin": pinyin[simplified][0],
                    "pinyin_frequency": str(pinyin[simplified][1]),
                    "match_kind": "to-verb" if gloss.startswith("to ") else "exact",
                    "english_gloss": gloss,
                    "cedict_pinyin": cedict_pinyin,
                    "traditional": traditional,
                    "source_line": str(line_number),
                    "packed_gloss_key": "yes" if simplified in base else "no",
                    "base_senses": " | ".join(f"{sense} [{pos}]" for sense, pos in base.get(simplified, [])),
                    "ecdict_translation": ecdict.get(word, {}).get("translation", ""),
                }
                candidates[(word, simplified, gloss)] = row

    headers = (
        "word", "targets", "pos", "chinese", "pinyin", "pinyin_frequency",
        "match_kind", "english_gloss", "cedict_pinyin", "traditional", "source_line",
        "packed_gloss_key", "base_senses", "ecdict_translation",
    )
    ordered = sorted(candidates.values(), key=lambda row: (
        -sum(target in row["targets"].split(",") for target in TARGETS),
        -int(row["pinyin_frequency"]), row["word"], row["chinese"],
    ))
    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / "candidates.tsv"
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(ordered)

    summary = {
        "batch": "exam-target-candidate-audit-1",
        "scope": list(TARGETS),
        "source": {
            "repo": PINNED_REPO,
            "commit": PINNED_COMMIT,
            "path": PINNED_PATH,
            "url": PINNED_URL,
            "license": "CC BY-SA 4.0",
            "sha256": sha(source),
            "bytes": source.stat().st_size,
        },
        "inputs": {
            "english_exam_tags_sha256": sha(tag_path),
            "ecdict_sha256": sha(ROOT / "build/vocabulary-research/skywind3000__ECDICT/ecdict.csv"),
            "pinyin_candidates_sha256": sha(ROOT / "build/pinyin-candidates.tsv"),
        },
        "mapped_headwords_before": {
            target: len({word for word, mask in tags.items() if mask & (1 << BIT[target])} & current_words)
            for target in TARGETS
        },
        "missing_headwords_before": {target: len(missing_by_target[target]) for target in TARGETS},
        "parsed_cedict_entries": parsed_entries,
        "candidate_pairs": len(ordered),
        "candidate_headwords": len({row["word"] for row in ordered}),
        "candidate_headwords_by_target": {
            target: len({row["word"] for row in ordered if target in row["targets"].split(",")})
            for target in TARGETS
        },
        "candidate_headwords_with_new_packed_gloss_keys": len({
            row["word"] for row in ordered if row["packed_gloss_key"] == "no"
        }),
        "candidate_headwords_by_target_with_new_keys": {
            target: len({row["word"] for row in ordered
                         if target in row["targets"].split(",") and row["packed_gloss_key"] == "no"})
            for target in TARGETS
        },
        "candidate_file_sha256": sha(output),
        "candidate_rule": "Review only: exact whole CC-CEDICT English headword gloss (or to-verb form), target exam membership in the pinned tag index, exact simplified Chinese key in the packed pinyin candidates, bundled IPA; POS evidence is shown from pinned ECDICT when available. Existing English glossary key is not required because the runtime translator supports pinyin candidate keys with no base translation.",
        "limitation": "CC-CEDICT does not provide POS. Every selected sense and POS needs human review; new Chinese keys are valid pinyin candidates but have no original English gloss entry.",
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
