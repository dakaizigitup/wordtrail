"""Audit Wiktionary-derived Open Dictionary v2.0 against Wordtrail exam gaps.

This script writes only a review queue under build/. The upstream dictionary
contains generated Chinese learner glosses, so no row is automatically shipped.
"""
from __future__ import annotations

import collections
import csv
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
sys.path.insert(0, str(ROOT / "scripts"))
from prepare_cet_batch import load_base
from exam_targets import load_exam_tags, RUNTIME_EXPANSIONS

SOURCE = ROOT / "build/source-audit/exam-targets/open-dictionary-v2/distribution.jsonl.gz"
OUT = ROOT / "build/source-audit/exam-targets/open-dictionary-v2-candidates.tsv"
SUMMARY = ROOT / "build/source-audit/exam-targets/open-dictionary-v2-candidates.json"
SOURCE_SHA256 = "69af69cdc685b5dce465613d1cc8fffb598eb46714f57cf73bd6606c2ceb7e43"
TARGETS = ("tem4", "tem8", "toefl", "ielts")
TARGET_BITS = {target: bit for bit, target in enumerate(("cet4", "cet6", *TARGETS))}
POS = {"noun": "n.", "verb": "v.", "adjective": "adj.", "adverb": "adv."}
WORD = re.compile(r"[a-z]+(?:[-'][a-z]+)*\Z")
CHINESE = re.compile(r"[\u3400-\u9fff]{2,6}\Z")
RUNTIME_FILES = RUNTIME_EXPANSIONS


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if not SOURCE.is_file() or sha(SOURCE) != SOURCE_SHA256:
        raise SystemExit("Missing or changed pinned Open Dictionary v2.0 release artifact")
    base = load_base(ROOT / "build/expansion-base.tsv")
    tags = load_exam_tags(DATA)
    ipa = {line.split("\t", 1)[0].strip().casefold()
           for filename in ("en_UK.txt", "en_US.txt")
           for line in (ROOT / "pronunciation/source" / filename).read_text(encoding="utf-8").splitlines()
           if "\t" in line}
    pinyin = {}
    for line in (ROOT / "build/pinyin-candidates.tsv").read_text(encoding="utf-8").splitlines():
        fields = line.split("\t")
        if len(fields) >= 3:
            pinyin[fields[0]] = (fields[1].replace(" ", ""), int(fields[2]))
    existing_words = {word for senses in base.values() for word, _ in senses}
    extras = collections.defaultdict(list)
    for filename in RUNTIME_FILES:
        path = ROOT / "vocabulary/data" / filename
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            fields = line.split("\t")
            if len(fields) != 4:
                raise SystemExit(f"Malformed runtime expansion row: {path}")
            chinese, word, pos, _source = fields
            existing_words.add(word)
            extras[chinese].append((word, pos))
    counts = collections.Counter({key: len(rows) for key, rows in extras.items()})
    rejects = collections.Counter()
    candidates = {}
    with gzip.open(SOURCE, "rt", encoding="utf-8") as stream:
        for line in stream:
            entry = json.loads(line)
            word = str(entry.get("normalized_headword") or entry.get("headword") or "").casefold()
            if not WORD.fullmatch(word):
                rejects["invalid_headword"] += 1
                continue
            if word not in tags or not any(tags[word] & (1 << TARGET_BITS[target]) for target in TARGETS):
                continue
            if word in existing_words:
                rejects["already_mapped"] += 1
                continue
            if word not in ipa:
                rejects["missing_ipa"] += 1
                continue
            if entry.get("entry_type") != "standard" or entry.get("proper_name"):
                rejects["nonstandard_or_proper_name"] += 1
                continue
            for group in entry.get("pos_groups", []):
                pos = POS.get(str(group.get("pos", "")).casefold())
                if not pos:
                    continue
                for meaning in group.get("meanings", []):
                    priority = str(meaning.get("priority", ""))
                    chinese = str(meaning.get("short_gloss", "")).strip()
                    if priority not in {"core", "common"} or not CHINESE.fullmatch(chinese):
                        continue
                    if chinese not in base:
                        rejects["no_packed_gloss_key"] += 1
                        continue
                    if chinese not in pinyin:
                        rejects["no_pinyin_candidate"] += 1
                        continue
                    if pos not in {base_pos for _, base_pos in base[chinese]}:
                        rejects["base_pos_mismatch"] += 1
                        continue
                    if counts[chinese] >= 8:
                        rejects["per_key_capacity"] += 1
                        continue
                    mask = tags[word]
                    targets = [target for target in TARGETS if mask & (1 << TARGET_BITS[target])]
                    key = (word, chinese, pos)
                    candidate = {
                        "word": word, "chinese": chinese, "pos": pos,
                        "targets": ",".join(targets), "priority": priority,
                        "pinyin": pinyin[chinese][0], "pinyin_frequency": str(pinyin[chinese][1]),
                        "source_sense_id": str(meaning.get("sense_id", "")),
                        "source_pos": str(group.get("pos", "")),
                        "source_short_gloss": chinese,
                        "base_senses": " | ".join(f"{text} [{base_pos}]" for text, base_pos in base[chinese]),
                        "source_headword_summary": str(entry.get("headword_summary", "")),
                        "source_learner_explanation": str(meaning.get("learner_explanation", "")),
                        "source_schema": str(entry.get("schema_version", "")),
                    }
                    rank = (0 if priority == "core" else 1,
                            -len(targets), -pinyin[chinese][1], chinese, pos)
                    if key not in candidates or rank < candidates[key][0]:
                        candidates[key] = (rank, candidate)

    rows = [pair[1] for pair in candidates.values()]
    # One new Chinese mapping per English word; prefer core senses, more target
    # labels, and common pinyin keys. Keep the full candidate pool in the TSV.
    rows.sort(key=lambda row: (0 if row["priority"] == "core" else 1,
                               -len(row["targets"].split(",")),
                               -int(row["pinyin_frequency"]), row["word"], row["chinese"]))
    headers = tuple(rows[0]) if rows else ("word", "chinese", "pos", "targets")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    by_target = {target: len({row["word"] for row in rows if target in row["targets"].split(",")}) for target in TARGETS}
    summary = {
        "source": "ahpxex/open-dictionary v2.0 distribution.jsonl.gz",
        "source_url": "https://github.com/ahpxex/open-dictionary/releases/download/v2.0/distribution.jsonl.gz",
        "source_sha256": SOURCE_SHA256,
        "source_license": "CC BY-SA 4.0; Wiktionary-derived and requires attribution/share-alike",
        "rows": len(rows), "headwords": len({row["word"] for row in rows}),
        "headwords_by_target": by_target,
        "candidate_rules": ["target-list headword", "not already mapped", "bundled IPA", "entry_type=standard", "not proper name", "core/common short_gloss", "2-6 Han characters", "exact packed Chinese key and POS", "exact existing pinyin candidate", "runtime max 8 extra senses/key"],
        "limitations": "LLM-generated learner glosses; this is a review queue only and is not included in the runtime dictionary.",
        "rejected": dict(sorted(rejects.items())),
        "output_sha256": sha(OUT),
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
