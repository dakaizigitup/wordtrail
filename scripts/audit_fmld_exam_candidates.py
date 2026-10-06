"""Audit the pinned FMLD text dictionary for unmapped exam headwords.

FMLD is used as a candidate source only. This script writes a review queue
under build/ and never changes runtime vocabulary.
"""
from __future__ import annotations

import collections
import csv
import argparse
import hashlib
import json
import re
from pathlib import Path

from prepare_cet_batch import load_base
from exam_targets import load_exam_tags, RUNTIME_EXPANSIONS

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
COMMIT = "de1a3c543fb35ede7f46e335d12f28572578c2b6"
SOURCE = ROOT / f"build/source-audit/exam-targets/fmld/{COMMIT}/fmld.en.txt"
SOURCE_SHA256 = "adffa622f223b33b03e76fd1d8f7c57cd90f6491cd5e9cec69a984ec1b3bc1ad"
OUT = ROOT / "build/source-audit/exam-targets/fmld-candidates.tsv"
SUMMARY = ROOT / "build/source-audit/exam-targets/fmld-candidates.json"
TARGETS = ("tem4", "tem8", "toefl", "ielts")
TARGET_BITS = {target: bit for bit, target in enumerate(("cet4", "cet6", *TARGETS))}
POS = {
    "noun": "n.", "verb": "v.", "verb-object": "v.",
    "adj": "adj.", "adjective": "adj.", "adv": "adv.",
    "pron": "pron.", "det": "det.", "conj": "conj.",
    "prep": "prep.", "intj": "int.", "num": "num.",
}
WORD = re.compile(r"[a-z]+(?:[-'][a-z]+)*\Z")
HAN = re.compile(r"[\u3400-\u9fff]{2,6}\Z")
RUNTIME_FILES = RUNTIME_EXPANSIONS


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_headword(line: str) -> tuple[str, set[str]]:
    fields = line.split("|", 2)
    if len(fields) != 3:
        return "", set()
    tags = {tag for tag in fields[1].split(";") if tag}
    word = fields[2].split(";", 1)[0].strip()
    return word, tags


def exact_english_glosses(text: str, target_words: set[str]) -> set[str]:
    result = set()
    for gloss in text.split(";"):
        value = gloss.strip().casefold().rstrip(" .,;:!?)}]").lstrip("([{\"")
        value = re.sub(r"\s+", " ", value)
        if value in target_words or (value.startswith("to ") and value[3:] in target_words):
            result.add(value[3:] if value.startswith("to ") else value)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-pos-mismatch", action="store_true",
                        help="keep rows whose FMLD POS differs from an existing Chinese-key POS")
    parser.add_argument("--allow-new-key", action="store_true",
                        help="keep pinyin candidate keys with no current English glossary entry")
    args = parser.parse_args()
    if not SOURCE.is_file() or sha(SOURCE) != SOURCE_SHA256:
        raise SystemExit("Missing or changed pinned FMLD dictionary snapshot")
    base = load_base(ROOT / "build/expansion-base.tsv")
    tags = load_exam_tags(DATA)
    target_words = {word for word, mask in tags.items()
                    if any(mask & (1 << TARGET_BITS[target]) for target in TARGETS)}
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
        path = DATA / filename
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            chinese, word, pos, _source = line.split("\t")
            existing_words.add(word)
            extras[chinese].append((word, pos))
    cap = collections.Counter({key: len(rows) for key, rows in extras.items()})
    reject = collections.Counter()
    candidates = {}
    current_word = ""
    current_tags: set[str] = set()
    current_pos = ""
    entries = 0
    with SOURCE.open(encoding="utf-8") as stream:
        for line_number, raw in enumerate(stream, 1):
            line = raw.rstrip("\r\n")
            if line.startswith("W"):
                current_word, current_tags = parse_headword(line)
                current_pos = ""
                entries += 1
                continue
            stripped = line.lstrip()
            if stripped.startswith("C ") or stripped.startswith("C\t"):
                current_pos = POS.get(stripped[1:].strip().casefold(), "")
                continue
            if not stripped.startswith("D"):
                continue
            if not current_pos or not current_word or not HAN.fullmatch(current_word):
                continue
            if current_word not in pinyin:
                reject["no_pinyin_candidate"] += 1
                continue
            base_senses = base.get(current_word, [])
            if current_word not in base and not args.allow_new_key:
                reject["no_packed_gloss_key"] += 1
                continue
            if base_senses and current_pos not in {pos for _, pos in base_senses}:
                if not args.allow_pos_mismatch:
                    reject["base_pos_mismatch"] += 1
                    continue
            parts = stripped.split("|", 2)
            if len(parts) < 3:
                continue
            for word in exact_english_glosses(parts[2], target_words):
                if word in existing_words:
                    reject["already_mapped"] += 1
                    continue
                if word not in ipa:
                    reject["missing_ipa"] += 1
                    continue
                mask = tags[word]
                wanted = [target for target in TARGETS if mask & (1 << TARGET_BITS[target])]
                key = (word, current_word, current_pos)
                row = {
                    "word": word, "chinese": current_word, "pos": current_pos,
                    "targets": ",".join(wanted),
                    "source_tags": ",".join(sorted(current_tags)),
                    "source_class": current_pos,
                    "source_definition_id": parts[0].strip(),
                    "source_line": str(line_number),
                    "english_gloss": parts[2].strip(),
                    "pinyin": pinyin[current_word][0],
                    "pinyin_frequency": str(pinyin[current_word][1]),
                    "base_pos_match": "yes" if current_pos in {pos for _, pos in base_senses} else ("new-key" if not base_senses else "no"),
                    "base_senses": " | ".join(f"{sense} [{pos}]" for sense, pos in base_senses),
                }
                candidates[key] = row
    ordered = sorted(candidates.values(), key=lambda row: (
        -sum(target in row["targets"].split(",") for target in TARGETS),
        -int(row["pinyin_frequency"]), row["word"], row["chinese"], row["source_definition_id"],
    ))
    headers = ("word", "chinese", "pos", "targets", "source_tags", "source_class",
               "source_definition_id", "source_line", "english_gloss", "pinyin",
               "pinyin_frequency", "base_pos_match", "base_senses")
    suffix = ("-relaxed-pos" if args.allow_pos_mismatch else "") + ("-new-key" if args.allow_new_key else "")
    output_path = OUT.with_name(OUT.stem + suffix + OUT.suffix)
    summary_path = SUMMARY.with_name(SUMMARY.stem + suffix + SUMMARY.suffix)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=headers, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(ordered)
    summary = {
        "batch": "fmld-exam-candidates-1",
        "source": {
            "repository": "jiong3/fmld", "commit": COMMIT,
            "path": "dict/fmld.en.txt", "sha256": SOURCE_SHA256,
            "license": "CC BY-SA 4.0; includes English Wiktionary/Kaikki and MDBG/CC-CEDICT data",
            "url": f"https://github.com/jiong3/fmld/blob/{COMMIT}/dict/fmld.en.txt",
        },
        "parsed_entries": entries,
        "candidate_pairs": len(ordered),
        "candidate_headwords": len({row["word"] for row in ordered}),
        "candidate_headwords_by_target": {
            target: len({row["word"] for row in ordered if target in row["targets"].split(",")})
            for target in TARGETS
        },
        "rules": ["fixed exam headword", "not already mapped", "exact full English gloss/headword or to-verb", "target IPA present", "exact Chinese key in pinyin candidates"] + ([] if args.allow_new_key else ["Chinese key exists in packed glossary"]) + ([] if args.allow_pos_mismatch else ["FMLD part of speech matches packed Chinese-key POS"]),
        "limitations": "Review queue only; FMLD is alpha and mixed-origin. Selected rows need review and source-specific attribution before runtime inclusion.",
        "rejected": dict(sorted(reject.items())),
        "output_sha256": sha(output_path),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
