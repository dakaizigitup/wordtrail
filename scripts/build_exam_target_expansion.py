"""Build a conservative, reviewable expansion batch for TEM/TOEFL/IELTS.

The automatic tranche uses only exact complete short Chinese glosses that are
already pinyin candidates and existing glossary keys with a matching POS.
Each English word receives at most one new Chinese key in this batch, and each
Chinese key remains under the runtime's eight-extra-sense cap.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
from pathlib import Path

from prepare_cet_batch import coverage, load_base

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
CANDIDATES = DATA / "batches/09-exam-target-candidate-review.tsv"
CANDIDATE_SUMMARY = DATA / "batches/09-exam-target-candidate-summary.json"
REVIEWED = DATA / "batches/09-exam-target-reviewed.tsv"
ECDICT_OUTPUT = DATA / "exam-target-ecdict-expansion.tsv"
KYLE_OUTPUT = DATA / "exam-target-kylebing-expansion.tsv"
MANIFEST = DATA / "exam-target-manifest.json"
PRIOR_RUNTIME_FILES = (
    "english-expansion.tsv", "wiktionary-expansion.tsv", "wiktionary-expansion-2.tsv",
    "cccedict-expansion.tsv", "cccedict-expansion-2.tsv", "cccedict-expansion-3.tsv",
    "cccedict-expansion-4.tsv",
)
TARGETS = ("cet4", "cet6", "tem4", "tem8", "toefl", "ielts")
TARGET_BITS = {target: bit for bit, target in enumerate(TARGETS)}
WORD = re.compile(r"[a-z]+(?:[-'][a-z]+)*\Z")
TIER_RANK = {"dual-source-wordnet": 0, "dual-source": 1, "ecdict-only": 2, "kyle-only": 3}
REVIEW_RULE = (
    "auto-v1: exact complete 2–6 Han-character gloss from one or both of ECDICT/KyleBing; exact current pinyin candidate and packed glossary key; "
    "matching POS in the packed key; exam membership and bundled IPA; one mapping per English headword; maximum eight added rows per Chinese key."
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def read_runtime(paths: tuple[str, ...] = PRIOR_RUNTIME_FILES) -> list[dict[str, str]]:
    rows = []
    for name in paths:
        path = DATA / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            fields = line.split("\t")
            if len(fields) != 4:
                raise ValueError(f"Invalid expansion row in {path}: {line!r}")
            rows.append(dict(zip(("chinese", "english", "pos", "source"), fields)))
    return rows


def load_tags() -> dict[str, int]:
    return {word: int(first) | int(second) for word, first, second in
            (line.split("\t") for line in (DATA / "english-tags.tsv").read_text(encoding="utf-8").splitlines())}


def load_ipa() -> set[str]:
    return {
        line.split("\t", 1)[0].strip().casefold()
        for name in ("en_UK.txt", "en_US.txt")
        for line in (ROOT / "pronunciation/source" / name).read_text(encoding="utf-8").splitlines()
        if "\t" in line
    }


def select_rows(candidates: list[dict[str, str]], base: dict[str, list[tuple[str, str]]],
                current: list[dict[str, str]], tags: dict[str, int], ipa: set[str],
                pinyin_keys: set[str]) -> tuple[list[dict[str, str]], dict[str, int]]:
    existing_words = {word for senses in base.values() for word, _ in senses}
    existing_words.update(row["english"] for row in current)
    extra_counts = collections.Counter(row["chinese"] for row in current)
    eligible = []
    rejected = collections.Counter()
    for row in candidates:
        word, chinese, pos = row["word"], row["chinese"], row["pos"]
        if not WORD.fullmatch(word):
            rejected["invalid_headword"] += 1
        elif word in existing_words:
            rejected["already_mapped"] += 1
        elif not (tags.get(word, 0) & 0b111100):
            rejected["not_in_target_exam_lists"] += 1
        elif chinese not in base or row["packed_gloss_key"] != "yes":
            rejected["no_packed_gloss_key"] += 1
        elif chinese not in pinyin_keys:
            rejected["no_pinyin_candidate"] += 1
        elif pos not in {sense_pos for _, sense_pos in base.get(chinese, [])}:
            rejected["base_pos_mismatch"] += 1
        elif row["ipa"] != "yes" or word not in ipa:
            rejected["missing_ipa"] += 1
        elif row["confidence_tier"] not in TIER_RANK:
            rejected["unknown_evidence_tier"] += 1
        else:
            eligible.append(row)

    eligible.sort(key=lambda row: (
        TIER_RANK[row["confidence_tier"]],
        -sum(target in row["targets"].split(",") for target in TARGETS[2:]),
        -int(row["pinyin_frequency"]),
        int(row["ecdict_frequency_rank"]),
        row["word"], row["chinese"], row["pos"],
    ))
    selected = []
    selected_words = set()
    for row in eligible:
        word, chinese = row["word"], row["chinese"]
        if word in selected_words:
            rejected["one_mapping_per_headword"] += 1
            continue
        if extra_counts[chinese] >= 8:
            rejected["per_key_capacity"] += 1
            continue
        source = "ECDICT MIT" if row["ecdict_exact_pos_gloss"] == "yes" else "KyleBing BSD-3-Clause"
        entry = dict(row)
        entry["runtime_source"] = source
        entry["review_rule"] = REVIEW_RULE
        selected.append(entry)
        selected_words.add(word)
        extra_counts[chinese] += 1
    return selected, rejected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write reviewed/runtime data and manifest")
    parser.add_argument("--check", action="store_true", help="verify existing outputs against deterministic generation")
    args = parser.parse_args()
    if not CANDIDATES.is_file() or not CANDIDATE_SUMMARY.is_file():
        raise SystemExit("Missing the pinned batch 09 candidate snapshot")
    candidate_summary = json.loads(CANDIDATE_SUMMARY.read_text(encoding="utf-8"))
    if candidate_summary["output_sha256"] != sha(CANDIDATES):
        raise SystemExit("Candidate audit checksum mismatch")
    base = load_base(ROOT / "build/expansion-base.tsv")
    candidates = read_tsv(CANDIDATES)
    current = read_runtime()
    tags = load_tags()
    ipa = load_ipa()
    pinyin_keys = {line.split("\t", 1)[0] for line in
                   (ROOT / "build/pinyin-candidates.tsv").read_text(encoding="utf-8").splitlines()}
    selected, rejected = select_rows(candidates, base, current, tags, ipa, pinyin_keys)
    ecdict_rows = [row for row in selected if row["runtime_source"] == "ECDICT MIT"]
    kyle_rows = [row for row in selected if row["runtime_source"] == "KyleBing BSD-3-Clause"]
    runtime_headers = ("chinese", "word", "pos", "runtime_source")
    ecdict_payload = "".join(f"{r['chinese']}\t{r['word']}\t{r['pos']}\tECDICT MIT\n" for r in ecdict_rows)
    kyle_payload = "".join(f"{r['chinese']}\t{r['word']}\t{r['pos']}\tKyleBing BSD-3-Clause\n" for r in kyle_rows)
    review_headers = (
        "word", "chinese", "pos", "targets", "runtime_source", "confidence_tier",
        "ecdict_exact_pos_gloss", "kyle_exact_pos_gloss", "wordnet_related_to_base_sense",
        "pinyin", "pinyin_frequency", "base_senses", "ecdict_translation", "kyle_sources", "review_rule",
    )
    review_payload = "\t".join(review_headers) + "\n" + "".join(
        "\t".join(row[name].replace("\t", " ").replace("\n", r"\n") for name in review_headers) + "\n"
        for row in selected
    )

    all_words = {word for senses in base.values() for word, _ in senses}
    all_words.update(row["english"] for row in current)
    all_words.update(row["word"] for row in selected)
    reachable_before = {word for chinese, senses in base.items() if chinese in pinyin_keys for word, _ in senses}
    reachable_before.update(row["english"] for row in current if row["chinese"] in pinyin_keys)
    reachable_after = reachable_before | {row["word"] for row in selected}
    before_coverage = coverage(tags, {word for senses in base.values() for word, _ in senses} | {row["english"] for row in current}, ipa)
    after_coverage = coverage(tags, all_words, ipa)
    reachable_before_coverage = coverage(tags, reachable_before, ipa)
    reachable_after_coverage = coverage(tags, reachable_after, ipa)
    input_hashes = {
        "candidate_summary_sha256": sha(CANDIDATE_SUMMARY),
        "candidate_tsv_sha256": sha(CANDIDATES),
        "english_tags_sha256": sha(DATA / "english-tags.tsv"),
        "pinyin_candidates_sha256": sha(ROOT / "build/pinyin-candidates.tsv"),
        "pinned_ecdict_sha256": next(row["sha256"] for row in json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))["input_files"] if row["path"] == "ecdict.csv"),
    }
    kyle_records = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))["input_files"]
    input_hashes["kylebing_exam_files"] = {
        target: next(row["sha256"] for row in kyle_records
                     if row["path"] == "full_line_jsonl/simple/正序/" + filename)
        for target, filename in (("tem4", "专四.jsonl"), ("tem8", "专八.jsonl"), ("toefl", "托福.jsonl"), ("ielts", "雅思.jsonl"))
    }
    manifest = {
        "batch": "09-exam-targets-auto-v1",
        "selection_rule": REVIEW_RULE,
        "coverage_before": before_coverage,
        "coverage_after": after_coverage,
        "pinyin_reachable_coverage_before": reachable_before_coverage,
        "pinyin_reachable_coverage_after": reachable_after_coverage,
        "added_pairs": len(selected),
        "added_headwords": len({row["word"] for row in selected}),
        "added_candidate_keys": len({row["chinese"] for row in selected}),
        "added_headwords_by_target": {
            target: len({row["word"] for row in selected if tags[row["word"]] & (1 << TARGET_BITS[target])})
            for target in TARGETS
        },
        "added_pairs_by_source": {"ecdict_mit": len(ecdict_rows), "kylebing_bsd_3_clause": len(kyle_rows)},
        "candidate_pairs": len(candidates),
        "candidate_headwords_by_target": candidate_summary["candidate_headwords_by_target"],
        "rejected_or_unselected_candidate_rows": dict(sorted(rejected.items())),
        "inputs": input_hashes,
        "runtime_files": {
            "exam-target-ecdict-expansion.tsv": {"sha256": hashlib.sha256(ecdict_payload.encode()).hexdigest(), "bytes": len(ecdict_payload.encode()), "rows": len(ecdict_rows)},
            "exam-target-kylebing-expansion.tsv": {"sha256": hashlib.sha256(kyle_payload.encode()).hexdigest(), "bytes": len(kyle_payload.encode()), "rows": len(kyle_rows)},
        },
        "reviewed_file": {"path": "batches/09-exam-target-reviewed.tsv", "sha256": hashlib.sha256(review_payload.encode()).hexdigest(), "rows": len(selected)},
        "licensing": "ECDICT-derived rows remain in a separate MIT-attributed runtime file; KyleBing-derived rows remain in a separate BSD-3-Clause-attributed runtime file. No complete source dictionary, examples, or audio are included.",
        "limitations": "Targets are fixed community wordlists, not official complete syllabi. Mapping coverage means at least one exact Chinese gloss mapping; candidate reachability means an exact pinyin key exists and may still require paging. This automatic tranche does not claim individual human review of every row.",
    }
    manifest_payload = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    expected = {
        REVIEWED: review_payload,
        ECDICT_OUTPUT: ecdict_payload,
        KYLE_OUTPUT: kyle_payload,
        MANIFEST: manifest_payload,
    }
    if args.check:
        changed = [str(path) for path, payload in expected.items()
                   if not path.exists() or path.read_text(encoding="utf-8") != payload]
        if changed:
            raise SystemExit("Exam-target generated data differs: " + ", ".join(changed))
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return
    if args.apply:
        for path, payload in expected.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload, encoding="utf-8", newline="\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
