"""Create a review-only queue using exact English/Chinese WordNet synsets.

The Chinese Open Wordnet is build-time evidence only. It never edits runtime
vocabulary automatically. A candidate must be an exact target headword, share
an English WordNet 3.0 synset with a Chinese Open Wordnet lemma, have a
ship-ready pinyin key and bundled IPA, and fit the runtime key limit.
"""
from __future__ import annotations

import collections
import csv
import hashlib
import json
import re
from pathlib import Path

from exam_targets import load_exam_tags, RUNTIME_EXPANSIONS
from prepare_cet_batch import load_base
from prepare_candidate_batch import parse_pinyin_candidates
from wordnet_guard import WordNetGuard


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
COMMIT = "406bf83b3c507a3d1f26e88252d5d66893fd36bf"
SOURCE = ROOT / "build/source-audit/omw-cow" / COMMIT / "wns/cow/wn-data-cmn.tab"
LICENSE = ROOT / "build/source-audit/omw-cow" / COMMIT / "wns/cow/LICENSE"
SOURCE_SHA256 = "379fd2e41d3e1395f9f27cf23a39c6181849ffb4020c14a07ed2a4d4dd651122"
LICENSE_SHA256 = "81a3cb1f97e120581d67c71424f2de5dd96325d951f991e8a092147a2a4b2321"
OUTPUT = ROOT / "build/source-audit/exam-targets/cow-candidates.tsv"
SUMMARY = ROOT / "build/source-audit/exam-targets/cow-candidates.json"
TARGETS = ("tem4", "tem8", "toefl", "ielts")
BITS = {target: bit for bit, target in enumerate(("cet4", "cet6", *TARGETS))}
WORD = re.compile(r"[a-z]+(?:[-'][a-z]+)*\Z")
SYNSET = re.compile(r"(?P<offset>\d{8})-(?P<pos>[nvar])\Z")
HAN = re.compile(r"[\u3400-\u9fff]{2,6}\Z")
MAX_EXTRA_PER_KEY = 8


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not SOURCE.is_file() or sha(SOURCE) != SOURCE_SHA256:
        raise SystemExit("Missing or changed pinned Chinese Open Wordnet source")
    if not LICENSE.is_file() or sha(LICENSE) != LICENSE_SHA256:
        raise SystemExit("Missing or changed pinned Chinese Open Wordnet license")

    tags = load_exam_tags(DATA)
    base = load_base(ROOT / "build/expansion-base.tsv")
    pinyin = parse_pinyin_candidates(ROOT / "build/pinyin-candidates.tsv")
    ipa = {
        line.split("\t", 1)[0].strip().casefold()
        for filename in ("en_UK.txt", "en_US.txt")
        for line in (ROOT / "pronunciation/source" / filename).read_text(encoding="utf-8").splitlines()
        if "\t" in line
    }
    mapped = {word for senses in base.values() for word, _ in senses}
    key_rows: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    for filename in RUNTIME_EXPANSIONS:
        path = DATA / filename
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            chinese, english, pos, _source = line.split("\t")
            mapped.add(english)
            key_rows[chinese].append((english, pos))
    cap = collections.Counter({key: len(rows) for key, rows in key_rows.items()})
    missing = {word for word, mask in tags.items() if mask and word not in mapped and WORD.fullmatch(word)}

    chinese_by_synset: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    rows_read = 0
    with SOURCE.open(encoding="utf-8") as stream:
        for raw in stream:
            if not raw.strip() or raw.startswith("#"):
                continue
            fields = raw.rstrip("\r\n").split("\t")
            if len(fields) != 3 or fields[1] != "cmn:lemma":
                continue
            match = SYNSET.fullmatch(fields[0])
            chinese = fields[2].strip()
            if match and HAN.fullmatch(chinese):
                chinese_by_synset[(match["pos"], match["offset"])].add(chinese)
                rows_read += 1

    guard = WordNetGuard()
    candidates: dict[tuple[str, str, str, str], dict[str, str]] = {}
    rejected = collections.Counter()
    for word in missing:
        if word not in ipa:
            rejected["missing_ipa"] += 1
            continue
        mask = tags[word]
        targets = [name for name, bit in BITS.items() if mask & (1 << bit)]
        for pos, pos_label in (("n", "n."), ("v", "v."), ("a", "adj."), ("r", "adv.")):
            for synset_pos, offset in guard.lemmas.get((pos, word), ()):
                if synset_pos != pos:
                    continue
                for chinese in chinese_by_synset.get((pos, offset), ()):
                    if chinese not in pinyin:
                        rejected["no_pinyin_candidate"] += 1
                        continue
                    if cap[chinese] >= MAX_EXTRA_PER_KEY:
                        rejected["key_capacity_full"] += 1
                        continue
                    key = (word, chinese, pos_label, offset)
                    candidates[key] = {
                        "word": word,
                        "chinese": chinese,
                        "pos": pos_label,
                        "targets": ",".join(targets),
                        "pinyin": pinyin[chinese][0],
                        "pinyin_frequency": str(pinyin[chinese][1]),
                        "synset_pos": pos,
                        "synset_offset": offset,
                        "base_senses": " | ".join(f"{sense} [{sense_pos}]" for sense, sense_pos in base.get(chinese, [])),
                        "runtime_key_count": str(cap[chinese]),
                    }

    ordered = sorted(candidates.values(), key=lambda row: (
        -sum(target in row["targets"].split(",") for target in TARGETS),
        -int(row["pinyin_frequency"]), row["word"], row["chinese"], row["synset_offset"],
    ))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    headers = (
        "word", "chinese", "pos", "targets", "pinyin", "pinyin_frequency",
        "synset_pos", "synset_offset", "base_senses", "runtime_key_count",
    )
    with OUTPUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(ordered)

    summary = {
        "source": "omwn/omw-data Chinese Open Wordnet (COW)",
        "commit": COMMIT,
        "source_path": "wns/cow/wn-data-cmn.tab",
        "source_sha256": SOURCE_SHA256,
        "license": "Chinese Open Wordnet per-file LICENSE (redistribution permitted with notice and disclaimer)",
        "license_sha256": LICENSE_SHA256,
        "rows_read": rows_read,
        "mapped_candidate_pairs": len(ordered),
        "candidate_headwords": len({row["word"] for row in ordered}),
        "candidate_headwords_by_target": {
            target: len({row["word"] for row in ordered if target in row["targets"].split(",")})
            for target in TARGETS
        },
        "rules": [
            "headword in pinned combined exam tags and not previously mapped",
            "exact shared English WordNet 3.0 synset and Chinese Open Wordnet lemma",
            "same part of speech",
            "exact 2-6 Han-character current pinyin candidate key",
            "bundled UK or US IPA",
            "runtime expansion key count below eight",
        ],
        "limitations": "Review-only candidates. Synset identity is strong lexical evidence but does not validate every Chinese gloss for learner usage or register.",
        "rejected": dict(sorted(rejected.items())),
        "output_sha256": sha(OUTPUT),
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
