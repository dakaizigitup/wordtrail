"""Audit and build the first professional-vocabulary tranche from pinned data.

Candidate discovery is offline and review-only. Runtime files are generated only
after every candidate has an explicit accept/reject decision in the curation TSV.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
SNAPSHOT_DIR = ROOT / "build/source-audit/kaikki-zh-english-2026.09.09"
DATABASE = SNAPSHOT_DIR / "lexhint-zh-english-dictionary-s10-2026.09.09.sqlite3"
ECDICT = ROOT / "build/vocabulary-research/skywind3000__ECDICT/ecdict.csv"
PINYIN = ROOT / "build/pinyin-candidates.tsv"
BASELINE = ROOT / "build/expansion-base.tsv"
UK_IPA = ROOT / "pronunciation/source/en_UK.txt"
US_IPA = ROOT / "pronunciation/source/en_US.txt"
CURATION = DATA / "batches/14-professional-reviewed.tsv"
CANDIDATES = SNAPSHOT_DIR / "professional-review-candidates.tsv"
EVIDENCE = DATA / "batches/14-professional-domain-evidence.tsv"
TAGS = DATA / "professional-domain-tags.tsv"
EXPANSION = DATA / "professional-expansion.tsv"
MANIFEST = DATA / "professional-vocabulary-manifest.json"

EXPECTED = {
    "database": "98fef9ba82047d0eaba650c1da074810c135da3c90e1fdb59f2faf197d6b7dd2",
    "pinyin": "914f6894fff1f6033af6d8bb9858f6901aa2d1a960cd2afd8923f899584f1290",
    "baseline": "ed58a90825243beada4d759f2f90d55ccdb4d38fc8701dffd78090e3a0b21d35",
    "ecdict": "1a6947e04785db63613a92e14903cdae7954f7e84860b10e68e5c7cbb3f9c3cf",
    "uk_ipa": "221394caef0cf723b4f2df81a98ac33191293257b88aed5b1fb89466d3a0dc77",
    "us_ipa": "2af6f154a5c363275f052d1f85acedef38ed185ca9745aa4314be77f6b70de67",
}
CATEGORIES = {"computing": "computer", "business": "business", "medicine": "medical"}
CATEGORY_ORDER = ("computer", "business", "medical")
CATEGORY_BITS = {name: 1 << (6 + index) for index, name in enumerate(CATEGORY_ORDER)}
CATEGORY_LABELS = {"computer": "计算机", "business": "商务", "medical": "医学"}
SOURCE = "Wiktionary CC BY-SA 4.0"
MAX_EXTRA_PER_KEY = 8
WORD = re.compile(r"[a-z]+(?:[-'][a-z]+)*\Z")
TERM = re.compile(r"[a-z]+(?:[-'][a-z]+)*(?: [a-z]+(?:[-'][a-z]+)*)*\Z")
POS = {"noun": "n.", "verb": "v.", "adj": "adj.", "adv": "adv."}
REVIEW_FIELDS = (
    "chinese", "english", "pos", "domains", "source_glosses", "source_entry_ids",
    "source_sense_ids", "pinyin", "pinyin_frequency", "ecdict_rows", "review_decision",
    "review_note",
)

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "build/vocab-tools"))
from build_wiktionary_expansion import read_expansion  # noqa: E402
from exam_targets import RUNTIME_EXPANSIONS  # noqa: E402
from opencc import OpenCC  # noqa: E402
from prepare_candidate_batch import source_pos_glosses  # noqa: E402
from prepare_cet_batch import load_base  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_inputs() -> dict[str, str]:
    paths = {
        "database": DATABASE, "pinyin": PINYIN, "baseline": BASELINE,
        "ecdict": ECDICT, "uk_ipa": UK_IPA, "us_ipa": US_IPA,
    }
    actual = {}
    for name, path in paths.items():
        if not path.is_file():
            raise SystemExit("Missing pinned professional-vocabulary input: " + str(path))
        actual[name] = sha(path)
        if actual[name] != EXPECTED[name]:
            raise SystemExit(f"Pinned {name} SHA-256 mismatch: {actual[name]}")
    return actual


def inputs():
    baseline = load_base(BASELINE)
    pairs = {(chinese, word) for chinese, senses in baseline.items() for word, _ in senses}
    existing_words = {word for _, word in pairs}
    extras_by_key: collections.Counter[str] = collections.Counter()
    for filename in RUNTIME_EXPANSIONS:
        for row in read_expansion(DATA / filename):
            pairs.add((row["chinese"], row["english"]))
            existing_words.add(row["english"])
            extras_by_key[row["chinese"]] += 1

    pinyin: dict[str, tuple[str, int]] = {}
    for line in PINYIN.read_text(encoding="utf-8").splitlines():
        chinese, code, frequency = line.split("\t")
        pinyin[chinese] = (code, int(frequency))

    ipa = set()
    for path in (UK_IPA, US_IPA):
        for line in path.read_text(encoding="utf-8").splitlines():
            if "\t" in line:
                ipa.add(line.split("\t", 1)[0].strip().lower())

    ecdict: dict[str, set[tuple[str, str]]] = collections.defaultdict(set)
    ecdict_rows: dict[tuple[str, str, str], set[int]] = collections.defaultdict(set)
    with ECDICT.open(encoding="utf-8-sig", newline="") as stream:
        for line_number, row in enumerate(csv.DictReader(stream), start=2):
            word = row["word"].strip().casefold()
            for chinese, pos in source_pos_glosses(row["translation"]):
                ecdict[word].add((chinese, pos))
                ecdict_rows[(word, chinese, pos)].add(line_number)
    return baseline, pairs, existing_words, extras_by_key, pinyin, ipa, ecdict, ecdict_rows


def discover():
    baseline, pairs, existing_words, extras_by_key, pinyin, ipa, ecdict, ecdict_rows = inputs()
    converter = OpenCC("t2s")
    category_evidence: dict[tuple[str, str, str, str], dict] = {}
    candidates: dict[tuple[str, str, str], dict] = {}
    connection = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True)
    try:
        query = """SELECT e.id, e.word, e.pos, s.id, s.glosses, s.topics
                   FROM entries e JOIN senses s ON s.entry_id=e.id
                   ORDER BY e.id, s.sense_index"""
        for entry_id, raw_chinese, raw_pos, sense_id, raw_glosses, raw_topics in connection.execute(query):
            pos = POS.get(raw_pos)
            if pos is None:
                continue
            chinese = converter.convert(raw_chinese).strip()
            if chinese not in pinyin:
                continue
            topics = set(json.loads(raw_topics))
            domains = sorted(CATEGORIES[topic] for topic in topics if topic in CATEGORIES)
            if not domains:
                continue
            pinyin_code, frequency = pinyin[chinese]
            for original_gloss in json.loads(raw_glosses):
                normalized = original_gloss.strip().casefold()
                english = normalized[3:].strip() if normalized.startswith("to ") else normalized
                if not TERM.fullmatch(english):
                    continue
                # Domain tags require an exact, currently reachable Chinese-English pair.
                if (chinese, english) in pairs:
                    for domain in domains:
                        key = (english, domain, chinese, pos)
                        row = category_evidence.setdefault(key, {
                            "english": english, "domain": domain, "chinese": chinese,
                            "pos": pos, "source_gloss": original_gloss,
                            "pinyin": pinyin_code, "pinyin_frequency": frequency,
                            "source_entry_id": entry_id, "source_sense_id": sense_id,
                            "mapping_status": "existing",
                        })
                        # Keep one deterministic source row per exact pair/domain.
                        if (entry_id, sense_id) < (row["source_entry_id"], row["source_sense_id"]):
                            row.update(source_gloss=original_gloss, source_entry_id=entry_id,
                                       source_sense_id=sense_id)

                # New mappings must add a genuinely new headword, have an exact same-POS
                # ECDICT Chinese gloss, a real pinyin candidate, IPA, and spare key capacity.
                if english in existing_words or (chinese, english) in pairs:
                    continue
                if not WORD.fullmatch(english):
                    continue
                if english not in ipa or (chinese, pos) not in ecdict.get(english, set()):
                    continue
                if extras_by_key[chinese] >= MAX_EXTRA_PER_KEY:
                    continue
                key = (chinese, english, pos)
                row = candidates.setdefault(key, {
                    "chinese": chinese, "english": english, "pos": pos,
                    "domains": set(), "source_glosses": set(), "source_entry_ids": set(),
                    "source_sense_ids": set(), "source_records": set(), "pinyin": pinyin_code,
                    "pinyin_frequency": frequency, "ecdict_rows": set(),
                })
                row["domains"].update(domains)
                row["source_glosses"].add(original_gloss)
                row["source_entry_ids"].add(str(entry_id))
                row["source_sense_ids"].add(str(sense_id))
                row["source_records"].add((entry_id, sense_id, original_gloss, tuple(domains)))
                row["ecdict_rows"].update(ecdict_rows[(english, chinese, pos)])
    finally:
        connection.close()
    return baseline, pairs, pinyin, category_evidence, candidates


def candidate_rows(candidates: dict) -> list[dict[str, str]]:
    rows = []
    for key in sorted(candidates):
        item = candidates[key]
        rows.append({
            "chinese": item["chinese"], "english": item["english"], "pos": item["pos"],
            "domains": ",".join(sorted(item["domains"])),
            "source_glosses": " | ".join(sorted(item["source_glosses"])),
            "source_entry_ids": ",".join(sorted(item["source_entry_ids"], key=int)),
            "source_sense_ids": ",".join(sorted(item["source_sense_ids"], key=int)),
            "pinyin": item["pinyin"], "pinyin_frequency": str(item["pinyin_frequency"]),
            "ecdict_rows": ",".join(map(str, sorted(item["ecdict_rows"]))),
        })
    return rows


def read_curation(path: Path, candidates: dict) -> tuple[list[dict], set[tuple[str, str, str]]]:
    if not path.is_file():
        raise SystemExit("Missing manual accept/reject decisions: " + str(path))
    expected = {tuple(row[field] for field in ("chinese", "english", "pos")): row for row in candidate_rows(candidates)}
    accepted = set()
    seen = set()
    reviewed = []
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if tuple(reader.fieldnames or ()) != REVIEW_FIELDS:
            raise SystemExit("Unexpected professional curation columns: " + str(reader.fieldnames))
        for row in reader:
            key = tuple(row[field] for field in ("chinese", "english", "pos"))
            if key in seen or key not in expected:
                raise SystemExit("Duplicate or stale professional decision: " + repr(key))
            seen.add(key)
            generated = expected[key]
            for field in REVIEW_FIELDS[:-2]:
                if row[field] != generated[field]:
                    raise SystemExit(f"Professional review evidence changed for {key}: {field}")
            if row["review_decision"] not in {"accept", "reject"} or not row["review_note"].strip():
                raise SystemExit("Every candidate needs an accept/reject decision and review note: " + repr(key))
            if row["review_decision"] == "accept":
                accepted.add(key)
            reviewed.append(row)
    if seen != set(expected):
        raise SystemExit(f"Incomplete review: {len(expected) - len(seen)} candidates have no decision")
    return reviewed, accepted


def build_outputs(hashes: dict[str, str]) -> dict[Path, bytes]:
    baseline, existing_pairs, pinyin, category_evidence, candidates = discover()
    reviewed, accepted = read_curation(CURATION, candidates)
    evidence = dict(category_evidence)
    expansions = []
    for chinese, english, pos in sorted(accepted):
        item = candidates[(chinese, english, pos)]
        expansions.append((chinese, english, pos, SOURCE))
        for entry_id, sense_id, source_gloss, domains in sorted(item["source_records"]):
            for domain in domains:
                key = (english, domain, chinese, pos)
                evidence.setdefault(key, {
                    "english": english, "domain": domain, "chinese": chinese,
                    "pos": pos, "source_gloss": source_gloss, "pinyin": item["pinyin"],
                    "pinyin_frequency": item["pinyin_frequency"],
                    "source_entry_id": int(entry_id), "source_sense_id": int(sense_id),
                    "mapping_status": "batch14",
                })

    tag_masks: dict[str, int] = collections.defaultdict(int)
    for (english, domain, _, _), _row in evidence.items():
        tag_masks[english] |= CATEGORY_BITS[domain]
    tag_payload = "".join(
        f"{word}\t{mask}\t{SOURCE}\n" for word, mask in sorted(tag_masks.items())
    ).encode("utf-8")
    expansion_payload = "".join("\t".join(row) + "\n" for row in expansions).encode("utf-8")
    evidence_fields = (
        "english", "domain", "chinese", "pos", "source_gloss", "pinyin",
        "pinyin_frequency", "source_entry_id", "source_sense_id", "mapping_status",
    )
    evidence_rows = sorted(evidence.values(), key=lambda row: (
        row["english"], row["domain"], row["chinese"], row["pos"],
        row["source_entry_id"], row["source_sense_id"],
    ))
    import io
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=evidence_fields, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for row in evidence_rows:
        writer.writerow({field: row[field] for field in evidence_fields})
    evidence_payload = buffer.getvalue().encode("utf-8")

    counts = {category: {
        "tagged_terms": sum(bool(mask & CATEGORY_BITS[category]) for mask in tag_masks.values()),
        "exact_candidate_pairs": sum(1 for row in evidence_rows if row["domain"] == category),
        "new_mappings": sum(1 for zh, word, _pos in accepted if category in candidates[(zh, word, _pos)]["domains"]),
    } for category in CATEGORY_ORDER}
    manifest = {
        "batch": "14-professional-domains-first-tranche",
        "categories": [
            {"id": name, "bit": 6 + i, "label": CATEGORY_LABELS[name],
             **counts[name]} for i, name in enumerate(CATEGORY_ORDER)
        ],
        "candidate_review": {
            "source": "pinned Kaikki/Wiktionary Chinese-English snapshot plus exact same-POS ECDICT cross-check",
            "candidate_pairs": len(candidates),
            "accepted_mappings": len(accepted),
            "rejected_mappings": len(candidates) - len(accepted),
            "curation_file": CURATION.relative_to(DATA).as_posix(),
            "curation_sha256": sha(CURATION),
        },
        "data_source": {
            "project": "English Wiktionary contributors via Kaikki/Wiktextract",
            "snapshot": "lexhint-zh-english-dictionary-s10-2026.09.09.sqlite3",
            "snapshot_sha256": hashes["database"],
            "wiktionary_upstream_sha256": "2fa05a70de03fc0d8a3855a70b1e2c7d?see wiktionary-manifest-2.json",
            "license": "CC BY-SA 4.0; source entries additionally available under GFDL",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "changes": "Selected exact glossary headwords and short complete phrases; traditional headwords normalized to simplified; retained category membership only for exact pinyin-reachable pairs. No source definitions or examples are included.",
        },
        "input_sha256": hashes,
        "outputs": {
            "professional-domain-tags.tsv": {"rows": len(tag_masks), "sha256": hashlib.sha256(tag_payload).hexdigest()},
            "professional-expansion.tsv": {"rows": len(expansions), "sha256": hashlib.sha256(expansion_payload).hexdigest()},
            "batches/14-professional-domain-evidence.tsv": {"rows": len(evidence_rows), "sha256": hashlib.sha256(evidence_payload).hexdigest()},
        },
        "scope_note": "Community topic classification, not an official curriculum. Domain tags are independent of exam tags and never reorder Chinese candidates.",
    }
    # Keep source hash exactly sourced from the fixed snapshot manifest.
    manifest["data_source"]["wiktionary_upstream_sha256"] = "2fa05a70de03fc0d8a3855a70e0b56c6087078571eb39173da4acb54df87e68"
    manifest_payload = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return {
        TAGS: tag_payload, EXPANSION: expansion_payload,
        EVIDENCE: evidence_payload, MANIFEST: manifest_payload,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates-only", action="store_true", help="write the review-only candidate queue")
    parser.add_argument("--apply", action="store_true", help="write generated runtime/evidence files")
    args = parser.parse_args()
    hashes = verify_inputs()
    _baseline, _pairs, _pinyin, _evidence, candidates = discover()
    rows = candidate_rows(candidates)
    if args.candidates_only:
        CANDIDATES.parent.mkdir(parents=True, exist_ok=True)
        with CANDIDATES.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=REVIEW_FIELDS[:-2], delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        print(json.dumps({"candidate_pairs": len(rows), "candidate_headwords": len({r['english'] for r in rows}),
                          "path": str(CANDIDATES), "sha256": sha(CANDIDATES)}, ensure_ascii=False, indent=2))
        return
    outputs = build_outputs(hashes)
    for path, payload in outputs.items():
        if args.apply:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        elif not path.is_file() or path.read_bytes() != payload:
            raise SystemExit("Generated professional vocabulary differs; run with --apply: " + str(path))
    print(json.dumps({"candidate_pairs": len(rows), "accepted_mappings": len(read_curation(CURATION, candidates)[1]),
                      "outputs": [str(path) for path in outputs]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
