"""Build the reviewed NAER high-school information-terms tranche."""
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
SOURCE_CSV = DATA / "sources/naer/information-basic-terms-2026-08-12.csv"
SOURCE_METADATA = DATA / "sources/naer/information-basic-dataset.json"
SOURCE_SHA256 = "9931846343405436c5487a1c491a75c7522d93436d75722816cf2e23a6dc10fc"
SOURCE_METADATA_SHA256 = "28b4da053388f3f4ad4987f6d968303ec363227c1294994e290b72efdb12bad6"
PREFILTER = DATA / "batches/38-naer-information-prefilter.tsv"
CANDIDATES = DATA / "batches/38-naer-information-candidates.tsv"
REVIEWED = DATA / "batches/38-naer-information-reviewed.tsv"
TAG_REVIEWED = DATA / "batches/38-naer-information-tags-reviewed.tsv"
EXPANSION = DATA / "naer-information-expansion.tsv"
TAGS = DATA / "naer-information-tags.tsv"
MANIFEST = DATA / "naer-information-manifest.json"

SOURCE = "NAER Information Terms (High School and Below) OGDL v1.0"
COMPUTER_BIT = 1 << 6
WORD = re.compile(r"[a-z][a-z'-]*\Z")
VARIANT_SEPARATOR = re.compile(r"[；;、，,/／|]+")

PREFILTER_FIELDS = (
    "english", "chinese", "source_chinese", "source_records", "source_urls",
    "pinyin", "pinyin_frequency", "ipa_sources", "ecdict_exact_noun_glosses",
    "already_mapped", "existing_headword", "already_computer_tag", "spare_capacity",
)
REVIEW_FIELDS = PREFILTER_FIELDS + ("decision", "review_note")
TAG_FIELDS = ("english", "source_records", "source_pairs", "already_computer_tag", "decision", "review_note")

ACCEPTED_PAIRS = {
    ("分割", "partition"),
    ("十进制", "decimal"),
    ("喇叭", "speaker"),
    ("目录", "directory"),
}
REJECTED_PAIRS = {
    ("流通", "currency"): (
        "The source also lists 货币, which is the suitable computing/data-format sense of currency. "
        "流通 is not a reliable standalone Chinese translation for this English headword."
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
        raise SystemExit("Pinned NAER information terms CSV SHA-256 mismatch")
    metadata_bytes = SOURCE_METADATA.read_bytes()
    if sha(metadata_bytes) != SOURCE_METADATA_SHA256:
        raise SystemExit("Pinned NAER information terms metadata SHA-256 mismatch")
    metadata = json.loads(metadata_bytes.decode("utf-8-sig"))
    if metadata.get("dataset_id") != "15407" or metadata.get("snapshot_sha256") != SOURCE_SHA256:
        raise SystemExit("Unexpected NAER information terms metadata")

    sys.path.insert(0, str(ROOT / "scripts"))
    import build_finance_i18n_batch as base

    inputs = base.load_inputs()
    expansion_source = (ROOT / "vocabulary/src/expansion/mod.rs").read_text(encoding="utf-8")
    compiled = set(re.findall(r'include_str!\("\.\./\.\./data/([^" ]+\.tsv)"\)', expansion_source))
    runtime_files = sorted(compiled - {EXPANSION.name})
    for filename in runtime_files:
        for line in (DATA / filename).read_text(encoding="utf-8").splitlines():
            fields = line.split("\t")
            if len(fields) < 3:
                continue
            chinese, english = fields[0], fields[1].casefold()
            pair = (chinese, english)
            if pair not in inputs["pairs"]:
                inputs["pairs"].add(pair)
                inputs["extras"][chinese] = inputs["extras"].get(chinese, 0) + 1
            inputs["words"].add(english)
    inputs["runtime_files"] = runtime_files
    inputs["runtime_hashes"] = {name: sha((DATA / name).read_bytes()) for name in runtime_files}

    lib_source = (ROOT / "vocabulary/src/lib.rs").read_text(encoding="utf-8")
    tag_files = sorted(set(re.findall(r'include_str!\("\.\./data/([^" ]+-tags\.tsv)"\)', lib_source)))
    existing_computer_tags = set()
    for filename in tag_files:
        if filename == TAGS.name:
            continue
        for line in (DATA / filename).read_text(encoding="utf-8").splitlines():
            fields = line.split("\t")
            if len(fields) >= 2 and fields[1].isdigit() and int(fields[1]) & COMPUTER_BIT:
                existing_computer_tags.add(fields[0].casefold())
    inputs["existing_computer_tags"] = existing_computer_tags
    return inputs


def discover(inputs: dict) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    grouped: dict[tuple[str, str], dict] = {}
    ipa_words = inputs["uk"] | inputs["us"]
    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        expected = ("序號", "英文名稱", "中文名稱", "來源網站")
        if tuple(reader.fieldnames or ()) != expected:
            raise SystemExit(f"Unexpected NAER information CSV columns: {reader.fieldnames}")
        for source in reader:
            english = source["英文名稱"].strip().casefold().strip("()")
            if not WORD.fullmatch(english) or english not in ipa_words:
                continue
            noun_glosses = {gloss for gloss, pos in inputs["ecdict"].get(english, ()) if pos == "n."}
            if not noun_glosses:
                continue
            for raw_chinese in VARIANT_SEPARATOR.split(source["中文名稱"].strip()):
                source_chinese = raw_chinese.strip()
                chinese = inputs["converter"].convert(source_chinese).strip()
                if not chinese or chinese not in inputs["pinyin"] or chinese not in noun_glosses:
                    continue
                pair = (chinese, english)
                item = grouped.setdefault(pair, {"rows": set(), "source_chinese": set(), "source_urls": set()})
                item["rows"].add(source["序號"].strip())
                item["source_chinese"].add(source_chinese)
                item["source_urls"].add(source["來源網站"].strip())

    prefilter = []
    for (chinese, english), item in sorted(grouped.items()):
        pinyin, frequency = inputs["pinyin"][chinese]
        prefilter.append({
            "english": english,
            "chinese": chinese,
            "source_chinese": " | ".join(sorted(item["source_chinese"])),
            "source_records": ",".join(sorted(item["rows"], key=int)),
            "source_urls": " | ".join(sorted(item["source_urls"])),
            "pinyin": pinyin,
            "pinyin_frequency": str(frequency),
            "ipa_sources": ",".join(name for name, words in (("UK", inputs["uk"]), ("US", inputs["us"])) if english in words),
            "ecdict_exact_noun_glosses": " | ".join(sorted(g for g, pos in inputs["ecdict"].get(english, ()) if pos == "n." and g == chinese)),
            "already_mapped": str((chinese, english) in inputs["pairs"]).lower(),
            "existing_headword": str(english in inputs["words"]).lower(),
            "already_computer_tag": str(english in inputs["existing_computer_tags"]).lower(),
            "spare_capacity": str(inputs["extras"].get(chinese, 0) < 8).lower(),
        })
    candidates = [row.copy() for row in prefilter if row["already_mapped"] == "false" and row["spare_capacity"] == "true"]
    return prefilter, candidates


def review(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    decisions = {
        **{pair: ("accept", "") for pair in ACCEPTED_PAIRS},
        **{pair: ("reject", note) for pair, note in REJECTED_PAIRS.items()},
    }
    candidate_keys = {(row["chinese"], row["english"]) for row in candidates}
    if candidate_keys != set(decisions):
        raise SystemExit(
            "NAER information-terms review coverage mismatch: "
            f"unreviewed={sorted(candidate_keys - set(decisions))}; unexpected={sorted(set(decisions) - candidate_keys)}"
        )
    output = []
    for row in candidates:
        pair = (row["chinese"], row["english"])
        decision, note = decisions[pair]
        if decision == "accept":
            note = (
                "Accepted after review: the NAER information-terms source supplies this bilingual term; "
                "the English headword matches the exact local ECDICT noun gloss and has local IPA and a "
                "reachable pinyin key. The concise mapping is useful in the listed information-technology sense."
            )
        output.append({**row, "decision": decision, "review_note": note})
    return output


def source_row_funnel(inputs: dict) -> dict[str, int]:
    counts: Counter[str] = Counter()
    ipa_words = inputs["uk"] | inputs["us"]
    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as stream:
        for source in csv.DictReader(stream):
            counts["source_records"] += 1
            english = source["英文名稱"].strip().casefold().strip("()")
            if not WORD.fullmatch(english):
                counts["multiword_or_non_headword"] += 1
                continue
            if english not in ipa_words:
                counts["single_word_without_local_ipa"] += 1
                continue
            noun_glosses = {gloss for gloss, pos in inputs["ecdict"].get(english, ()) if pos == "n."}
            if not noun_glosses:
                counts["single_word_without_local_noun_gloss"] += 1
                continue
            variants = [
                inputs["converter"].convert(raw.strip()).strip()
                for raw in VARIANT_SEPARATOR.split(source["中文名稱"].strip())
            ]
            exact_glosses = [variant for variant in variants if variant in noun_glosses]
            if not exact_glosses:
                counts["no_exact_local_noun_translation"] += 1
                continue
            if not any(gloss in inputs["pinyin"] for gloss in exact_glosses):
                counts["exact_local_noun_translation_without_pinyin"] += 1
                continue
            counts["eligible_source_records"] += 1
    return dict(counts)


def build(prefilter: list[dict[str, str]], candidates: list[dict[str, str]], reviewed: list[dict[str, str]], inputs: dict) -> dict:
    accepted = [row for row in reviewed if row["decision"] == "accept"]
    rejected = [row for row in reviewed if row["decision"] == "reject"]
    per_key: Counter[str] = Counter()
    expansion_rows = []
    for row in accepted:
        chinese, english = row["chinese"], row["english"]
        if (chinese, english) in inputs["pairs"] or chinese not in inputs["pinyin"]:
            raise SystemExit(f"Accepted NAER information mapping is already mapped or unreachable: {chinese} -> {english}")
        if inputs["extras"].get(chinese, 0) + per_key[chinese] >= 8:
            raise SystemExit(f"Accepted NAER information mapping exceeds per-key expansion limit: {chinese} -> {english}")
        per_key[chinese] += 1
        expansion_rows.append({"chinese": chinese, "english": english, "pos": "n.", "source": SOURCE})
    expansion_rows.sort(key=lambda row: (row["chinese"], row["english"]))

    exact_by_word: dict[str, list[dict[str, str]]] = {}
    for row in prefilter:
        exact_by_word.setdefault(row["english"], []).append(row)
    tag_rows = [{"english": word, "mask": str(COMPUTER_BIT), "source": SOURCE} for word in sorted(exact_by_word)]
    tag_review_rows = []
    for word, matching in sorted(exact_by_word.items()):
        tag_review_rows.append({
            "english": word,
            "source_records": ",".join(sorted({n for row in matching for n in row["source_records"].split(",")}, key=int)),
            "source_pairs": " | ".join(f"{row['chinese']} -> {word}" for row in matching),
            "already_computer_tag": str(word in inputs["existing_computer_tags"]).lower(),
            "decision": "accept",
            "review_note": (
                "Accepted as a computer-category source membership: this single-word headword occurs in the "
                "official NAER information-terms snapshot and has an exact local noun gloss, IPA, and reachable "
                "pinyin mapping. Membership records source scope; it does not claim every English sense is computing-specific."
            ),
        })

    outputs = {
        PREFILTER.relative_to(DATA).as_posix(): write_tsv(PREFILTER, PREFILTER_FIELDS, prefilter),
        CANDIDATES.relative_to(DATA).as_posix(): write_tsv(CANDIDATES, PREFILTER_FIELDS, candidates),
        REVIEWED.relative_to(DATA).as_posix(): write_tsv(REVIEWED, REVIEW_FIELDS, reviewed),
        TAG_REVIEWED.relative_to(DATA).as_posix(): write_tsv(TAG_REVIEWED, TAG_FIELDS, tag_review_rows),
        EXPANSION.relative_to(DATA).as_posix(): write_tsv(EXPANSION, ("chinese", "english", "pos", "source"), expansion_rows, header=False),
        TAGS.relative_to(DATA).as_posix(): write_tsv(TAGS, ("english", "mask", "source"), tag_rows, header=False),
    }
    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as stream:
        source_count = sum(1 for _ in csv.DictReader(stream))
    metadata = json.loads(SOURCE_METADATA.read_text(encoding="utf-8-sig"))
    new_headwords = sorted({row["english"] for row in accepted if row["existing_headword"] == "false"})
    manifest = {
        "batch": "38-naer-information-terms-high-school-below",
        "source": {
            "title": metadata["title"],
            "provider": metadata["provider"],
            "dataset_id": metadata["dataset_id"],
            "dataset_url": metadata["dataset_url"],
            "resource_url": metadata["resource_url"],
            "license": metadata["license"],
            "license_url": metadata["license_url"],
            "portal_updated_at": metadata["portal_updated_at"],
            "snapshot_sha256": SOURCE_SHA256,
            "snapshot_bytes": SOURCE_CSV.stat().st_size,
            "records": source_count,
        },
        "filters": {
            "mapping_scope": "Single-word English entries with exact local ECDICT noun gloss, UK or US IPA, reachable local pinyin key, and local expansion capacity.",
            "candidate_scope": "Every eligible previously unmapped pair receives an explicit accept/reject decision; only concise reviewed standalone mappings enter runtime data.",
            "computer_tag_scope": "Source membership is added for eligible single-word terms in the official information-terms dataset; membership does not imply every English sense is computing-specific.",
            "traditional_to_simplified": "Traditional Chinese source variants are normalized using OpenCC t2s before exact matching.",
            "runtime_per_key_cap": 8,
        },
        "counts": {
            "source_records": source_count,
            "eligible_exact_pairs": len(prefilter),
            "already_mapped_pairs": sum(row["already_mapped"] == "true" for row in prefilter),
            "capacity_blocked_pairs": sum(row["already_mapped"] == "false" and row["spare_capacity"] == "false" for row in prefilter),
            "new_review_candidates": len(candidates),
            "accepted_mappings": len(accepted),
            "rejected_candidates": len(rejected),
            "new_english_headwords": len(new_headwords),
            "computer_tag_source_memberships": len(tag_rows),
            "new_computer_tag_memberships": len({row["english"] for row in tag_rows} - inputs["existing_computer_tags"]),
            "reviewed_tag_headwords": len(tag_review_rows),
        },
        "source_row_funnel": source_row_funnel(inputs),
        "accepted_pairs": [f"{row['chinese']} -> {row['english']} (n.)" for row in accepted],
        "rejected_pairs": [{"pair": f"{row['chinese']} -> {row['english']}", "reason": row["review_note"]} for row in rejected],
        "source_hashes": {
            SOURCE_CSV.name: SOURCE_SHA256,
            SOURCE_METADATA.name: sha(SOURCE_METADATA.read_bytes()),
            **inputs["runtime_hashes"],
        },
        "base_lexicon_hashes": inputs["hashes"],
        "outputs": {name: sha(payload) for name, payload in outputs.items()},
        "runtime_note": f"Only {len(expansion_rows)} reviewed mappings and {len(tag_rows)} compact category-membership rows enter the once-initialized offline lookup; the {source_count:,}-row source CSV is never read while typing.",
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discover", action="store_true")
    args = parser.parse_args()
    inputs = load_inputs()
    prefilter, candidates = discover(inputs)
    if args.discover:
        print(json.dumps({
            "source_row_funnel": source_row_funnel(inputs),
            "eligible_exact_pairs": len(prefilter),
            "already_mapped_pairs": sum(row["already_mapped"] == "true" for row in prefilter),
            "new_mapping_candidates": candidates,
        }, ensure_ascii=False, indent=2))
        return
    manifest = build(prefilter, candidates, review(candidates), inputs)
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
