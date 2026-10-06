"""Build manually reviewed TEM8/TOEFL mappings backed by fixed dictionaries.

This batch uses OpenEtymology wordlist membership, an exact current pinyin key,
bundled IPA, and identical short-gloss/POS evidence from pinned ECDICT and
KyleBing entries. Every selected sense is recorded in a human review table.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
from pathlib import Path

from prepare_cet_batch import load_base

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
BATCH = DATA / "batches"
DECISIONS = BATCH / "10-openetymology-review-decisions.tsv"
CANDIDATES = BATCH / "09-exam-target-candidate-review.tsv"
CANDIDATE_SUMMARY = BATCH / "09-exam-target-candidate-summary.json"
OPEN_TAGS = DATA / "openetymology-exam-tags.tsv"
OPEN_TAG_MANIFEST = DATA / "openetymology-tags-manifest.json"
EXPANSION = DATA / "openetymology-exam-expansion.tsv"
REVIEWED = BATCH / "10-openetymology-reviewed.tsv"
MANIFEST = DATA / "openetymology-expansion-manifest.json"
TARGETS = ("cet4", "cet6", "tem4", "tem8", "toefl", "ielts")
TARGET_BIT = {name: 1 << bit for bit, name in enumerate(TARGETS)}
WORD = re.compile(r"[a-z]+(?:[-'][a-z]+)*\Z")
MAX_EXTRA_PER_KEY = 8
RUNTIME_FILES = (
    "english-expansion.tsv", "wiktionary-expansion.tsv", "wiktionary-expansion-2.tsv",
    "cccedict-expansion.tsv", "cccedict-expansion-2.tsv", "cccedict-expansion-3.tsv",
    "cccedict-expansion-4.tsv",
)


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def load_ipa() -> set[str]:
    return {
        line.split("\t", 1)[0].strip().casefold()
        for name in ("en_UK.txt", "en_US.txt")
        for line in (ROOT / "pronunciation/source" / name).read_text(encoding="utf-8").splitlines()
        if "\t" in line
    }


def build() -> tuple[dict[Path, bytes], dict[str, object]]:
    if not OPEN_TAGS.is_file() or not OPEN_TAG_MANIFEST.is_file():
        raise SystemExit("Build OpenEtymology tags first: py scripts/build_openetymology_tags.py")
    tag_manifest = json.loads(OPEN_TAG_MANIFEST.read_text(encoding="utf-8"))
    if sha(OPEN_TAGS.read_bytes()) != tag_manifest["output"]["sha256"]:
        raise SystemExit("OpenEtymology membership checksum mismatch")
    open_tags = {
        word: int(mask)
        for word, mask in (line.split("\t") for line in OPEN_TAGS.read_text(encoding="utf-8").splitlines())
    }
    candidate_summary = json.loads(CANDIDATE_SUMMARY.read_text(encoding="utf-8"))
    candidate_payload = CANDIDATES.read_bytes()
    if sha(candidate_payload) != candidate_summary["output_sha256"]:
        raise SystemExit("Pinned candidate review checksum mismatch")
    candidates = {
        (row["word"], row["chinese"], row["pos"]): row
        for row in read_tsv(CANDIDATES)
    }
    original_tags: dict[str, int] = {
        word: int(first) | int(second)
        for word, first, second in
        (line.split("\t") for line in (DATA / "english-tags.tsv").read_text(encoding="utf-8").splitlines())
    }
    decisions = read_tsv(DECISIONS)
    base = load_base(ROOT / "build/expansion-base.tsv")
    base_words = {word for senses in base.values() for word, _ in senses}
    pinyin_keys = {
        line.split("\t", 1)[0]
        for line in (ROOT / "build/pinyin-candidates.tsv").read_text(encoding="utf-8").splitlines()
    }
    ipa = load_ipa()
    current: list[dict[str, str]] = []
    for filename in RUNTIME_FILES:
        path = DATA / filename
        for line in path.read_text(encoding="utf-8").splitlines():
            chinese, english, pos, source = line.split("\t")
            current.append({"chinese": chinese, "english": english, "pos": pos, "source": source})
    for filename in ("exam-target-ecdict-expansion.tsv", "exam-target-kylebing-expansion.tsv"):
        for line in (DATA / filename).read_text(encoding="utf-8").splitlines():
            chinese, english, pos, source = line.split("\t")
            current.append({"chinese": chinese, "english": english, "pos": pos, "source": source})
    existing_words = base_words | {row["english"] for row in current}
    extra_counts = collections.Counter(row["chinese"] for row in current)
    selected: list[dict[str, str]] = []
    chosen_words: set[str] = set()
    for decision in decisions:
        word, chinese, pos = decision["word"], decision["chinese"], decision["pos"]
        key = (word, chinese, pos)
        evidence = candidates.get(key)
        if not WORD.fullmatch(word) or evidence is None:
            raise SystemExit("Decision is not an exact audited candidate: " + repr(key))
        if not (open_tags.get(word, 0) & (TARGET_BIT["tem8"] | TARGET_BIT["toefl"])):
            raise SystemExit("Decision is outside pinned OpenEtymology TEM8/TOEFL lists: " + word)
        if evidence["confidence_tier"] != "dual-source" or evidence["ecdict_exact_pos_gloss"] != "yes" or evidence["kyle_exact_pos_gloss"] != "yes":
            raise SystemExit("Decision lacks exact ECDICT/KyleBing agreement: " + word)
        if evidence["packed_gloss_key"] != "yes" or evidence["key_capacity_available"] != "yes":
            raise SystemExit("Decision lacks a packed key or available capacity: " + word)
        if word not in ipa or evidence["ipa"] != "yes" or chinese not in pinyin_keys:
            raise SystemExit("Decision lacks IPA or an exact pinyin candidate: " + word)
        if word in existing_words or word in chosen_words:
            raise SystemExit("Decision duplicates a mapped/selected English headword: " + word)
        if extra_counts[chinese] >= MAX_EXTRA_PER_KEY:
            escaped = chinese.encode("unicode_escape").decode("ascii")
            raise SystemExit(f"Decision exceeds per-key runtime expansion cap: {escaped}, word={word}, count={extra_counts[chinese]}")
        target_mask = open_tags[word]
        original_targets = [name for name in TARGETS if original_tags.get(word, 0) & TARGET_BIT[name]]
        new_targets = [name for name in ("tem8", "toefl") if target_mask & TARGET_BIT[name]]
        row = dict(evidence)
        row.update({
            "review_note": decision["review_note"],
            "targets": ",".join(name for name in TARGETS if name in original_targets or name in new_targets),
            "openetymology_targets": ",".join(new_targets),
            "runtime_source": "ECDICT MIT + KyleBing BSD-3-Clause",
            "openetymology_commit": tag_manifest["commit"],
        })
        selected.append(row)
        chosen_words.add(word)
        extra_counts[chinese] += 1

    runtime_payload = "".join(
        f"{row['chinese']}\t{row['word']}\t{row['pos']}\tECDICT MIT + KyleBing BSD-3-Clause\n"
        for row in sorted(selected, key=lambda item: (item["chinese"], item["word"], item["pos"]))
    ).encode("utf-8")
    review_fields = (
        "word", "chinese", "pos", "targets", "openetymology_targets", "runtime_source",
        "confidence_tier", "ecdict_exact_pos_gloss", "kyle_exact_pos_gloss",
        "pinyin", "pinyin_frequency", "base_senses", "ecdict_translation", "kyle_sources",
        "review_note", "openetymology_commit",
    )
    review_payload = "\t".join(review_fields) + "\n"
    review_payload += "".join(
        "\t".join(row.get(name, "").replace("\t", " ").replace("\n", r"\n") for name in review_fields) + "\n"
        for row in sorted(selected, key=lambda item: item["word"])
    )
    review_bytes = review_payload.encode("utf-8")
    mapped_before = base_words | {row["english"] for row in current}
    mapped_after = mapped_before | chosen_words
    pinyin_before = {word for chinese, senses in base.items() if chinese in pinyin_keys for word, _ in senses}
    pinyin_before.update(row["english"] for row in current if row["chinese"] in pinyin_keys)
    pinyin_after = pinyin_before | chosen_words
    combined_tags = dict(original_tags)
    for word, mask in open_tags.items():
        combined_tags[word] = combined_tags.get(word, 0) | mask

    def coverage(tags: dict[str, int], words: set[str]) -> dict[str, dict[str, int | float]]:
        result = {}
        for target in TARGETS:
            target_words = {word for word, mask in tags.items() if mask & TARGET_BIT[target]}
            count = len(target_words & words)
            result[target] = {
                "total": len(target_words), "mapped": count, "missing": len(target_words) - count,
                "percent": round(100 * count / len(target_words), 2) if target_words else 0.0,
            }
        return result

    open_list_words = {
        target: {word for word, mask in open_tags.items() if mask & TARGET_BIT[target]}
        for target in ("tem8", "toefl")
    }
    manifest = {
        "batch": "10-openetymology-tem8-toefl-reviewed-v1",
        "openetymology_commit": tag_manifest["commit"],
        "openetymology_tags_sha256": tag_manifest["output"]["sha256"],
        "candidate_queue_sha256": sha(candidate_payload),
        "decision_file_sha256": sha(DECISIONS.read_bytes()),
        "added_pairs": len(selected),
        "added_unique_headwords": len(chosen_words),
        "added_candidate_keys": len({row["chinese"] for row in selected}),
        "added_headwords_by_target": {
            target: len({row["word"] for row in selected if row["targets"] and target in row["targets"].split(",")})
            for target in TARGETS
        },
        "added_pairs_by_target": {
            target: sum(bool(row["targets"]) and target in row["targets"].split(",") for row in selected)
            for target in TARGETS
        },
        "coverage_before_combined_sources": coverage(combined_tags, mapped_before),
        "coverage_after_combined_sources": coverage(combined_tags, mapped_after),
        "pinyin_reachable_coverage_before_combined_sources": coverage(combined_tags, pinyin_before),
        "pinyin_reachable_coverage_after_combined_sources": coverage(combined_tags, pinyin_after),
        "openetymology_list_coverage_before": {
            target: {
                "total": len(words), "mapped": len(words & mapped_before),
                "missing": len(words - mapped_before),
                "percent": round(100 * len(words & mapped_before) / len(words), 2),
            }
            for target, words in open_list_words.items()
        },
        "openetymology_list_coverage_after": {
            target: {
                "total": len(words), "mapped": len(words & mapped_after),
                "missing": len(words - mapped_after),
                "percent": round(100 * len(words & mapped_after) / len(words), 2),
            }
            for target, words in open_list_words.items()
        },
        "runtime_file": {"path": EXPANSION.name, "rows": len(selected), "bytes": len(runtime_payload), "sha256": sha(runtime_payload)},
        "reviewed_file": {"path": REVIEWED.relative_to(DATA).as_posix(), "rows": len(selected), "sha256": sha(review_bytes)},
        "license": "CC BY-SA 4.0 for the list-derived selection and mapping table; dictionary-source attributions and notices for ECDICT (MIT) and KyleBing/english-vocabulary (BSD-3-Clause) are retained separately.",
        "selection_rule": "Manually reviewed exact headword-to-complete-short-gloss mapping; pinned ECDICT and KyleBing agree on the same word, Chinese gloss, and POS; headword occurs in pinned OpenEtymology TEM8 or TOEFL list; Chinese key is an exact shipped pinyin candidate; UK or US IPA exists; only previously unmapped headwords are added; max eight extra senses per key.",
        "limitation": "All target lists are community wordlists, not official complete syllabi. Coverage means at least one mapping in the selected wordlist; pinyin reachability does not guarantee first-page placement.",
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return {
        EXPANSION: runtime_payload,
        REVIEWED: review_bytes,
        MANIFEST: manifest_bytes,
    }, manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected, manifest = build()
    if args.check:
        changed = [str(path) for path, payload in expected.items() if not path.is_file() or path.read_bytes() != payload]
        if changed:
            raise SystemExit("OpenEtymology expansion differs: " + ", ".join(changed))
    else:
        for path, payload in expected.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
