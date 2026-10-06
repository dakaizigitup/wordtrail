"""Build the separately licensed, manually reviewed Wiktionary supplement."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

from prepare_cet_batch import coverage, load_base


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
BATCHES = DATA / "batches"
CURATION = BATCHES / "03-wiktionary-reviewed.tsv"
OUTPUT = DATA / "wiktionary-expansion.tsv"
MANIFEST = DATA / "wiktionary-manifest.json"
BASELINE = ROOT / "build/expansion-base.tsv"
PINYIN = ROOT / "build/pinyin-candidates.tsv"
SOURCE_LABEL = "Wiktionary CC BY-SA 4.0"
ALLOWED_POS = {"n.", "v.", "adj.", "adv."}
LIMIT = 8


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path: Path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def read_expansion(path: Path):
    names = ("chinese", "english", "pos", "source")
    return [dict(zip(names, line.split("\t"))) for line in path.read_text(encoding="utf-8").splitlines()]


def exam_inputs():
    tags = {}
    for line in (DATA / "english-tags.tsv").read_text(encoding="utf-8").splitlines():
        word, first_source_mask, second_source_mask = line.split("\t")
        tags[word] = int(first_source_mask) | int(second_source_mask)
    pinyin = {}
    for line in PINYIN.read_text(encoding="utf-8").splitlines():
        chinese, code, frequency = line.split("\t")
        pinyin[chinese] = (code, int(frequency))
    ipa = set()
    for filename in ("en_UK.txt", "en_US.txt"):
        for line in (ROOT / "pronunciation/source" / filename).read_text(encoding="utf-8").splitlines():
            if "\t" in line:
                ipa.add(line.split("\t", 1)[0].strip().lower())
    return tags, pinyin, ipa


def build_payloads(
    curation_path: Path = CURATION,
    output_path: Path = OUTPUT,
    manifest_path: Path = MANIFEST,
    batch_name: str = "02-wiktionary-1",
    prior_runtime_paths: tuple[Path, ...] = (),
    source_snapshot: dict | None = None,
):
    base = load_base(BASELINE)
    tags, pinyin, ipa = exam_inputs()
    original_expansion = read_expansion(DATA / "english-expansion.tsv")
    prior_rows = [row for path in prior_runtime_paths for row in read_expansion(path)]
    extra_by_key = {}
    existing_pairs = set()
    existing_words = {word for senses in base.values() for word, _ in senses}
    for row in original_expansion + prior_rows:
        chinese, word = row["chinese"], row["english"]
        extra_by_key.setdefault(chinese, []).append(word)
        existing_pairs.add((chinese, word))
        existing_words.add(word)

    curated = read_rows(curation_path)
    required_fields = {
        "chinese", "english", "pos", "targets", "sense", "source_lang", "source_url",
        "source_page_id", "source_revision_id", "source_revision_timestamp", "review_note",
    }
    if not curated or set(curated[0]) != required_fields:
        raise ValueError("Unexpected Wiktionary curation schema")

    seen = set()
    rows = []
    capacities = {key: LIMIT - len(words) for key, words in extra_by_key.items()}
    for item in curated:
        chinese, word, pos = item["chinese"], item["english"], item["pos"]
        key = (chinese, word, pos)
        if key in seen:
            raise ValueError("Duplicate curated Wiktionary pair: " + repr(key))
        seen.add(key)
        if not re.fullmatch(r"[a-z]+(?:[-'][a-z]+)*", word):
            raise ValueError("Invalid English headword: " + word)
        if pos not in ALLOWED_POS:
            raise ValueError("Unsupported English POS: " + pos)
        if not re.fullmatch(r"[\u4e00-\u9fff]{2,6}", chinese):
            raise ValueError("Chinese gloss must be a short complete word: " + chinese)
        if chinese not in base or chinese not in pinyin:
            raise ValueError("Chinese gloss is not an exact packed pinyin candidate: " + chinese)
        if word not in tags or not (tags[word] & 3):
            raise ValueError("Headword is not a CET4/CET6 tagged word: " + word)
        actual_targets = [target for bit, target in enumerate(("cet4", "cet6")) if tags[word] & (1 << bit)]
        if item["targets"].split(",") != actual_targets:
            raise ValueError("Exam labels disagree with the pinned tag index: " + word)
        if word in existing_words or (chinese, word) in existing_pairs:
            raise ValueError("Headword is already mapped in the current shipped vocabulary: " + word)
        if word not in ipa:
            raise ValueError("No bundled IPA pronunciation for new headword: " + word)
        if item["source_lang"] not in {"cmn", "zh"}:
            raise ValueError("Wiktionary translation is not marked Mandarin/Chinese: " + word)
        if not item["sense"].strip() or not item["review_note"].strip():
            raise ValueError("Every adopted translation needs a sense and a review note: " + word)
        if not re.fullmatch(r"[0-9]+", item["source_page_id"]):
            raise ValueError("Invalid source page ID: " + word)
        revision = item["source_revision_id"]
        if not re.fullmatch(r"[0-9]+", revision):
            raise ValueError("Invalid Wiktionary revision ID: " + word)
        if not item["source_url"].startswith("https://en.wiktionary.org/wiki/") or not item["source_url"].endswith("?oldid=" + revision):
            raise ValueError("Source URL must pin the cited Wiktionary revision: " + word)
        try:
            remaining = capacities[chinese]
        except KeyError:
            remaining = LIMIT
        if remaining <= 0:
            raise ValueError("The Chinese key has reached the eight-extra limit: " + chinese)
        capacities[chinese] = remaining - 1
        rows.append((chinese, word, pos, SOURCE_LABEL))

    payload = "".join("\t".join(row) + "\n" for row in rows).encode("utf-8")
    new_words = {row[1] for row in rows}
    old_words = existing_words
    new_all_words = old_words | new_words
    before_reachable = {
        word for chinese, senses in base.items() if chinese in pinyin for word, _ in senses
    } | {row["english"] for row in original_expansion + prior_rows if row["chinese"] in pinyin}
    after_reachable = before_reachable | new_words
    old_coverage = coverage(tags, old_words, ipa)
    new_coverage = coverage(tags, new_all_words, ipa)
    manifest = {
        "batch": batch_name,
        "source": {
            "project": "English Wiktionary",
            "url": "https://en.wiktionary.org/",
            "extraction": (
                "Pinned English Wiktionary Mandarin-entry revisions, with a fixed Kaikki-derived snapshot used only for candidate discovery; 2026-10-06 audit"
                if source_snapshot else "Wiktionary MediaWiki API; 2026-10-06 local audit"
            ),
            "translation_language": "Mandarin Chinese",
            "license": "CC BY-SA 4.0 (selected Wiktionary content is additionally available under GFDL)",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        },
        **({"discovery_snapshot": source_snapshot} if source_snapshot else {}),
        "curation_file": {
            "path": curation_path.relative_to(DATA).as_posix(),
            "sha256": sha(curation_path),
            "rows": len(curated),
        },
        "runtime_file": {
            "path": output_path.relative_to(DATA).as_posix(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
            "rows": len(rows),
        },
        "added_pairs": len(rows),
        "added_headwords": len(new_words),
        "added_candidate_keys": len({row[0] for row in rows}),
        "added_headwords_by_target": {
            target: sum(bool(tags[word] & (1 << bit)) for word in new_words)
            for bit, target in enumerate(("cet4", "cet6"))
        },
        "pending_before": sum(1 for word, mask in tags.items() if mask & 3 and word not in old_words),
        "pending_after": sum(1 for word, mask in tags.items() if mask & 3 and word not in new_all_words),
        "coverage_before": old_coverage,
        "coverage_after": new_coverage,
        "candidate_reachable_coverage_before": coverage(tags, before_reachable, ipa),
        "candidate_reachable_coverage_after": coverage(tags, after_reachable, ipa),
        "reachability_scope": "Reachability coverage includes original glossary words for every exact Chinese surface in the complete exported pinyin candidate index, including one-character keys. The Wiktionary additions themselves are restricted to 2-6 Han-character keys. The 0.1.13 short-gloss batch audit counted only 2-6 Han-character keys, so its 90.66%/86.46% figures are not directly comparable; under this complete-key scope its baseline is 91.64%/87.52%.",
        "review_rule": (
            "Each included row is an exact English gloss from a pinned Mandarin Wiktionary entry revision; the selected entry revision is the row's source of truth, while the fixed Kaikki-derived snapshot was used only to discover candidates. Every row was checked against its English sense and the local ECDICT short gloss, an exact packed Chinese pinyin key, and bundled English IPA. The data remains separate from MIT/BSD expansion files and carries CC BY-SA attribution."
            if source_snapshot else "Every included row is an exact English Wiktionary Mandarin translation in a pinned revision, manually checked against the entry sense and the local ECDICT short gloss, with an exact packed Chinese pinyin key and bundled English IPA. The dataset remains separate from the MIT/BSD expansion file and carries its own CC BY-SA attribution."
        ),
        "not_included": "Other Wiktionary candidates with no exact pinyin key, weak or mismatched sense/POS evidence, stigmatizing wording, or no bundled IPA remain excluded from runtime.",
        "license_boundary": f"The generated {output_path.name} and its source-attributed curation file are CC BY-SA 4.0 data. The adjacent software and ECDICT/KyleBing expansion files retain their own existing licenses.",
    }
    report_payload = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return {output_path: payload, manifest_path: report_payload}, manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="write generated data and manifest")
    args = parser.parse_args()
    outputs, manifest = build_payloads()
    for path, payload in outputs.items():
        if args.apply:
            path.write_bytes(payload)
        elif not path.is_file() or path.read_bytes() != payload:
            raise SystemExit(f"Generated file differs; run with --apply: {path}")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
