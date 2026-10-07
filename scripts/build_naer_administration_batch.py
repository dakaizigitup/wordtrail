"""Build the reviewed NAER administration vocabulary tranche."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
SOURCE_CSV = DATA / "sources/naer/administration-academic-terms-2026-08-12.csv"
SOURCE_METADATA = DATA / "sources/naer/administration-dataset.json"
SOURCE_SHA256 = "8faf844b2393fbb27f432a8a5df8e4194c6e64c8a0c7754b0a6242a7b2e4f05b"
PREFILTER = DATA / "batches/34-naer-administration-prefilter.tsv"
CANDIDATES = DATA / "batches/34-naer-administration-candidates.tsv"
REVIEWED = DATA / "batches/34-naer-administration-reviewed.tsv"
TAG_REVIEWED = DATA / "batches/34-naer-administration-tags-reviewed.tsv"
EXPANSION = DATA / "naer-administration-expansion.tsv"
TAGS = DATA / "naer-administration-tags.tsv"
MANIFEST = DATA / "naer-administration-manifest.json"

SOURCE = "NAER Administration Academic Terms OGDL v1.0"
ADMINISTRATION_BIT = 1 << 9
WORD = re.compile(r"[a-z][a-z'-]*\Z")
VARIANT_SEPARATOR = re.compile(r"[；;、，,/／|]+")

PREFILTER_FIELDS = (
    "english", "chinese", "source_chinese", "source_records", "source_urls",
    "pinyin", "pinyin_frequency", "ipa_sources", "ecdict_exact_noun_glosses",
    "already_mapped", "existing_headword", "spare_capacity",
)
REVIEW_FIELDS = PREFILTER_FIELDS + ("decision", "review_note")
TAG_FIELDS = ("english", "source_records", "source_pairs", "already_administration_tag", "decision", "review_note")

# The exact source/local noun-meaning candidates are reviewed explicitly.
# The majority are ordinary public-administration concepts; one broad sense is
# deferred because ECDICT's exact Chinese gloss needs a narrower context.
ACCEPTED_PAIRS = {
    ("假定", "assumption"),
    ("能力", "competence"),
    ("大会", "convention"),
    ("降级", "demotion"),
    ("分化", "differentiation"),
    ("多样化", "diversification"),
    ("公正", "equity"),
    ("假设", "hypothesis"),
    ("宣言", "manifesto"),
    ("国有化", "nationalization"),
    ("目的", "objective"),
    ("官员", "officer"),
    ("城邦", "polis"),
    ("政体", "polity"),
    ("试用", "probation"),
    ("自信", "self-confidence"),
    ("无私", "selflessness"),
}
DEFERRED_PAIRS = {
    ("调解", "reconciliation"): (
        "The official administration list supplies 调解 and the local dictionary has an exact noun gloss, "
        "but reconciliation is often 和解/调和 while 调解 more directly denotes mediation; defer pending narrower context."
    ),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_tsv(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]], *, header: bool = True) -> bytes:
    import io

    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t", lineterminator="\n")
    if header:
        writer.writeheader()
    writer.writerows(rows)
    payload = stream.getvalue().encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def load_inputs() -> dict:
    if sha(SOURCE_CSV.read_bytes()) != SOURCE_SHA256:
        raise SystemExit("Pinned NAER administration CSV SHA-256 mismatch")
    metadata = json.loads(SOURCE_METADATA.read_text(encoding="utf-8-sig"))
    if metadata.get("dataset_id") != "15262" or metadata.get("snapshot_sha256") != SOURCE_SHA256:
        raise SystemExit("Unexpected NAER administration dataset metadata")

    sys.path.insert(0, str(ROOT / "scripts"))
    import build_naer_management_batch as management_batch

    inputs = management_batch.load_inputs(exclude_runtime_files={EXPANSION.name})
    lib_source = (ROOT / "vocabulary/src/lib.rs").read_text(encoding="utf-8")
    tag_files = sorted(set(re.findall(r'include_str!\("\.\./data/([^" ]+-tags\.tsv)"\)', lib_source)) - {TAGS.name})
    administration_words = set()
    for filename in tag_files:
        for line in (DATA / filename).read_text(encoding="utf-8").splitlines():
            fields = line.split("\t")
            if len(fields) >= 2 and fields[1].isdigit() and int(fields[1]) & ADMINISTRATION_BIT:
                administration_words.add(fields[0].casefold())
    inputs["existing_administration_words"] = administration_words
    return inputs


def discover(inputs: dict) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    grouped: dict[tuple[str, str], dict] = {}
    ipa_words = inputs["uk"] | inputs["us"]
    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        expected = ("序號", "英文名稱", "中文名稱", "來源網站")
        if tuple(reader.fieldnames or ()) != expected:
            raise SystemExit(f"Unexpected NAER administration CSV columns: {reader.fieldnames}")
        for row in reader:
            english = row["英文名稱"].strip().casefold().strip("()")
            if not WORD.fullmatch(english) or english not in ipa_words:
                continue
            noun_glosses = {gloss for gloss, pos in inputs["ecdict"].get(english, ()) if pos == "n."}
            if not noun_glosses:
                continue
            for raw_chinese in VARIANT_SEPARATOR.split(row["中文名稱"].strip()):
                chinese = inputs["converter"].convert(raw_chinese.strip()).strip()
                if not chinese or chinese not in inputs["pinyin"] or chinese not in noun_glosses:
                    continue
                pair = (chinese, english)
                record = grouped.setdefault(pair, {"rows": set(), "source_chinese": set(), "source_urls": set()})
                record["rows"].add(row["序號"].strip())
                record["source_chinese"].add(raw_chinese.strip())
                record["source_urls"].add(row["來源網站"].strip())

    prefilter = []
    for (chinese, english), evidence in sorted(grouped.items()):
        pinyin, frequency = inputs["pinyin"][chinese]
        prefilter.append({
            "english": english,
            "chinese": chinese,
            "source_chinese": " | ".join(sorted(evidence["source_chinese"])),
            "source_records": ",".join(sorted(evidence["rows"], key=int)),
            "source_urls": " | ".join(sorted(evidence["source_urls"])),
            "pinyin": pinyin,
            "pinyin_frequency": str(frequency),
            "ipa_sources": ",".join(name for name, words in (("UK", inputs["uk"]), ("US", inputs["us"])) if english in words),
            "ecdict_exact_noun_glosses": " | ".join(sorted(noun_glosses for noun_glosses, pos in inputs["ecdict"].get(english, ()) if pos == "n." and noun_glosses == chinese)),
            "already_mapped": str((chinese, english) in inputs["pairs"]).lower(),
            "existing_headword": str(english in inputs["words"]).lower(),
            "spare_capacity": str(inputs["extras"].get(chinese, 0) < 8).lower(),
        })
    candidates = [row.copy() for row in prefilter if row["already_mapped"] == "false" and row["spare_capacity"] == "true"]
    return prefilter, candidates


def review(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    decisions = {
        **{pair: ("accept", "") for pair in ACCEPTED_PAIRS},
        **{pair: ("defer", note) for pair, note in DEFERRED_PAIRS.items()},
    }
    keys = {(row["chinese"], row["english"]) for row in candidates}
    if keys != set(decisions):
        raise SystemExit(
            "NAER administration review coverage mismatch: "
            f"unreviewed={sorted(keys - set(decisions))}; unexpected={sorted(set(decisions) - keys)}"
        )
    rows = []
    for row in candidates:
        decision, note = decisions[(row["chinese"], row["english"])]
        if decision == "accept":
            note = (
                "Accepted after review: the NAER administration term, exact local ECDICT noun gloss, "
                "and available pinyin/IPA support a coherent public-administration, political-science, "
                "or administrative-management sense."
            )
        rows.append({**row, "decision": decision, "review_note": note})
    return rows


def build(prefilter: list[dict[str, str]], candidates: list[dict[str, str]], reviewed: list[dict[str, str]], inputs: dict) -> dict:
    accepted = [row for row in reviewed if row["decision"] == "accept"]
    deferred = [row for row in reviewed if row["decision"] == "defer"]
    per_key: Counter[str] = Counter()
    expansion_rows = []
    for row in accepted:
        chinese, english = row["chinese"], row["english"]
        if (chinese, english) in inputs["pairs"] or chinese not in inputs["pinyin"]:
            raise SystemExit(f"Accepted NAER administration mapping is already mapped or unreachable: {chinese} -> {english}")
        if inputs["extras"].get(chinese, 0) + per_key[chinese] >= 8:
            raise SystemExit(f"Accepted NAER administration mapping exceeds per-key expansion limit: {chinese} -> {english}")
        per_key[chinese] += 1
        expansion_rows.append({"chinese": chinese, "english": english, "pos": "n.", "source": SOURCE})
    expansion_rows.sort(key=lambda row: (row["chinese"], row["english"]))

    exact_by_word: dict[str, list[dict[str, str]]] = {}
    for row in prefilter:
        exact_by_word.setdefault(row["english"], []).append(row)
    tag_rows = [{"english": word, "mask": str(ADMINISTRATION_BIT), "source": SOURCE} for word in sorted(exact_by_word)]
    tag_review_rows = []
    for word, matching in sorted(exact_by_word.items()):
        tag_review_rows.append({
            "english": word,
            "source_records": ",".join(sorted({number for row in matching for number in row["source_records"].split(",")}, key=int)),
            "source_pairs": " | ".join(f"{row['chinese']} -> {word}" for row in matching),
            "already_administration_tag": str(word in inputs["existing_administration_words"]).lower(),
            "decision": "accept",
            "review_note": (
                "Accepted as an administration-domain membership: the English headword is explicitly listed "
                "in the official NAER Administration Academic Terms snapshot, with local exact noun meaning, IPA, and pinyin evidence."
            ),
        })
    for row in accepted:
        if row["english"] not in exact_by_word:
            raise SystemExit(f"Accepted administration mapping lacks a source-membership record: {row['english']}")

    prefilter_bytes = write_tsv(PREFILTER, PREFILTER_FIELDS, prefilter)
    candidate_bytes = write_tsv(CANDIDATES, PREFILTER_FIELDS, candidates)
    reviewed_bytes = write_tsv(REVIEWED, REVIEW_FIELDS, reviewed)
    tag_review_bytes = write_tsv(TAG_REVIEWED, TAG_FIELDS, tag_review_rows)
    expansion_bytes = write_tsv(EXPANSION, ("chinese", "english", "pos", "source"), expansion_rows, header=False)
    tags_bytes = write_tsv(TAGS, ("english", "mask", "source"), tag_rows, header=False)

    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as stream:
        source_record_count = sum(1 for _ in csv.DictReader(stream))
    metadata = json.loads(SOURCE_METADATA.read_text(encoding="utf-8-sig"))
    manifest = {
        "batch": "34-naer-administration-terms",
        "source": {
            "title": "National Academy for Educational Research - Administration Academic Terms",
            "provider": "National Academy for Educational Research",
            "dataset_id": "15262",
            "dataset_url": "https://data.gov.tw/dataset/15262",
            "resource_url": "https://opendata.naer.edu.tw/學術名詞/國家教育研究院-行政學學術名詞.csv",
            "license": "Open Government Data License v1.0",
            "license_url": "https://data.gov.tw/license",
            "portal_updated_at": metadata["portal_updated_at"],
            "snapshot_sha256": SOURCE_SHA256,
            "snapshot_bytes": SOURCE_CSV.stat().st_size,
            "records": source_record_count,
        },
        "filters": {
            "source_scope": "Single-word English entries with exact local ECDICT noun gloss, UK or US IPA, reachable local pinyin key, and local expansion capacity.",
            "candidate_scope": "Every previously unmapped eligible pair receives an explicit accept/defer decision; only reviewed concise standalone mappings enter runtime data.",
            "administration_tag_scope": "A word receives the administration category when it is explicitly present in the official NAER Administration Academic Terms snapshot and has exact local noun, IPA, and pinyin evidence.",
            "traditional_to_simplified": "Input snapshot is simplified Chinese; OpenCC normalization is retained for consistent matching.",
            "runtime_per_key_cap": 8,
        },
        "counts": {
            "source_records": source_record_count,
            "eligible_exact_pairs": len(prefilter),
            "already_mapped_pairs": sum(row["already_mapped"] == "true" for row in prefilter),
            "new_review_candidates": len(candidates),
            "accepted_mappings": len(accepted),
            "deferred_candidates": len(deferred),
            "new_english_headwords": len({row["english"] for row in accepted if row["existing_headword"] == "false"}),
            "administration_tag_source_memberships": len(tag_rows),
            "new_administration_tag_memberships": len({row["english"] for row in tag_rows} - inputs["existing_administration_words"]),
            "reviewed_tag_headwords": len(tag_review_rows),
        },
        "accepted_pairs": [f"{row['chinese']} -> {row['english']} (n.)" for row in accepted],
        "deferred_pairs": [f"{row['chinese']} -> {row['english']} (n.)" for row in deferred],
        "source_hashes": {
            SOURCE_CSV.name: SOURCE_SHA256,
            SOURCE_METADATA.name: sha(SOURCE_METADATA.read_bytes()),
            **inputs["runtime_hashes"],
        },
        "base_lexicon_hashes": inputs["hashes"],
        "outputs": {
            PREFILTER.relative_to(DATA).as_posix(): sha(prefilter_bytes),
            CANDIDATES.relative_to(DATA).as_posix(): sha(candidate_bytes),
            REVIEWED.relative_to(DATA).as_posix(): sha(reviewed_bytes),
            TAG_REVIEWED.relative_to(DATA).as_posix(): sha(tag_review_bytes),
            EXPANSION.relative_to(DATA).as_posix(): sha(expansion_bytes),
            TAGS.relative_to(DATA).as_posix(): sha(tags_bytes),
        },
        "runtime_note": "Only reviewed compact mappings and administration membership rows enter offline lookup; the 3,737-row source CSV is never read while typing.",
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discover", action="store_true")
    args = parser.parse_args()
    inputs = load_inputs()
    prefilter, candidates = discover(inputs)
    reviewed = review(candidates)
    if args.discover:
        print(json.dumps({
            "eligible_exact_pairs": len(prefilter),
            "already_mapped_pairs": sum(row["already_mapped"] == "true" for row in prefilter),
            "new_review_candidates": len(candidates),
            "accepted": sum(row["decision"] == "accept" for row in reviewed),
            "deferred": sum(row["decision"] == "defer" for row in reviewed),
        }, ensure_ascii=False, indent=2))
        return
    manifest = build(prefilter, candidates, reviewed, inputs)
    print(json.dumps(manifest["counts"], ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
