"""Build the reviewed NAER education vocabulary tranche."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
SOURCE_CSV = DATA / "sources/naer/education-terminology-2026-06-01.csv"
SOURCE_METADATA = DATA / "sources/naer/education-dataset.json"
SOURCE_SHA256 = "b674073b959c749546cac19ef867d27a908ee492d39f69cec4bc4c2dcdcaed57"
PREFILTER = DATA / "batches/35-naer-education-prefilter.tsv"
CANDIDATES = DATA / "batches/35-naer-education-candidates.tsv"
REVIEWED = DATA / "batches/35-naer-education-reviewed.tsv"
TAG_REVIEWED = DATA / "batches/35-naer-education-tags-reviewed.tsv"
EXPANSION = DATA / "naer-education-expansion.tsv"
TAGS = DATA / "naer-education-tags.tsv"
MANIFEST = DATA / "naer-education-manifest.json"

SOURCE = "NAER Education Terminology OGDL v1.0"
EDUCATION_BIT = 1 << 10
WORD = re.compile(r"[a-z][a-z'-]*\Z")
VARIANT_SEPARATOR = re.compile(r"[；;、，,/／|]+")

PREFILTER_FIELDS = (
    "english", "chinese", "source_chinese", "source_records", "source_urls",
    "pinyin", "pinyin_frequency", "ipa_sources", "ecdict_exact_noun_glosses",
    "already_mapped", "existing_headword", "spare_capacity",
)
REVIEW_FIELDS = PREFILTER_FIELDS + ("decision", "review_note")
TAG_FIELDS = ("english", "source_records", "source_pairs", "already_education_tag", "decision", "review_note")

ACCEPTED_PAIRS = {
    ("适应", "adaptation"),
    ("出席", "attendance"),
    ("分类", "classification"),
    ("分级", "classification"),
    ("示范", "demonstration"),
    ("教化", "cultivation"),
    ("免除", "exemption"),
    ("毕业", "graduation"),
    ("视察", "inspection"),
    ("学院", "institute"),
    ("教导", "instruction"),
    ("讲师", "instructor"),
    ("内省", "introspection"),
    ("国语", "mandarin"),
    ("心理", "mind"),
    ("分数", "point"),
    ("休息", "recess"),
    ("背诵", "recital"),
    ("院长", "rector"),
    ("同学", "schoolmate"),
    ("自治", "self-government"),
    ("感觉", "sensation"),
    ("思考", "thinking"),
}
REJECTED_PAIRS = {
    ("修道院", "cloister"): "The source/local pair names a monastery or cloister, not a useful standalone education term.",
    ("开始", "commencement"): "The local gloss is a generic beginning; in education commencement usually refers to a graduation ceremony, so this pair is not equivalent.",
    ("徽章", "insignia"): "The gloss denotes an insignia generally and the source gives no education-specific meaning.",
    ("操作", "manipulation"): "The local noun gloss is too broad and the source provides no pedagogical context.",
    ("格言", "maxim"): "A maxim is a general saying; the source does not establish a distinct education-domain sense.",
    ("神经质", "nervousness"): "Nervousness means anxiety or apprehension; 神经质 more directly means neuroticism and is not an exact translation.",
    ("占有", "occupation"): "Occupation usually means a job or activity in this context; 占有 is not a reliable translation.",
    ("长官", "prefect"): "A school prefect is usually a student monitor; the broad gloss 长官 can mislead without a narrower context.",
    ("同情", "sympathy"): "The translation is generic and no specific educational or pedagogical sense is evidenced.",
    ("休会", "recess"): "休会 refers to an adjournment of a meeting or legislative session; it does not match the school-break sense of recess.",
}
DEFERRED_PAIRS = {
    ("免职", "dismissal"): "Could refer to dismissal of school personnel, but the source gives no education-specific context; defer.",
    ("学派", "school"): "Could mean a school of thought in education theory, but this standalone source record does not disambiguate that sense; defer.",
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
        raise SystemExit("Pinned NAER education CSV SHA-256 mismatch")
    metadata = json.loads(SOURCE_METADATA.read_text(encoding="utf-8-sig"))
    if metadata.get("dataset_id") != "6319" or metadata.get("snapshot_sha256") != SOURCE_SHA256:
        raise SystemExit("Unexpected NAER education dataset metadata")

    sys.path.insert(0, str(ROOT / "scripts"))
    import build_naer_management_batch as management_batch

    inputs = management_batch.load_inputs(exclude_runtime_files={EXPANSION.name})
    lib_source = (ROOT / "vocabulary/src/lib.rs").read_text(encoding="utf-8")
    tag_files = sorted(set(re.findall(r'include_str!\("\.\./data/([^" ]+-tags\.tsv)"\)', lib_source)) - {TAGS.name})
    education_words = set()
    for filename in tag_files:
        for line in (DATA / filename).read_text(encoding="utf-8").splitlines():
            fields = line.split("\t")
            if len(fields) >= 2 and fields[1].isdigit() and int(fields[1]) & EDUCATION_BIT:
                education_words.add(fields[0].casefold())
    inputs["existing_education_words"] = education_words
    return inputs


def discover(inputs: dict) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    grouped: dict[tuple[str, str], dict] = {}
    ipa_words = inputs["uk"] | inputs["us"]
    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        expected = ("序號", "英文名稱", "中文名稱", "來源網站")
        if tuple(reader.fieldnames or ()) != expected:
            raise SystemExit(f"Unexpected NAER education CSV columns: {reader.fieldnames}")
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
            "ecdict_exact_noun_glosses": " | ".join(sorted(g for g, pos in inputs["ecdict"].get(english, ()) if pos == "n." and g == chinese)),
            "already_mapped": str((chinese, english) in inputs["pairs"]).lower(),
            "existing_headword": str(english in inputs["words"]).lower(),
            "spare_capacity": str(inputs["extras"].get(chinese, 0) < 8).lower(),
        })
    candidates = [row.copy() for row in prefilter if row["already_mapped"] == "false" and row["spare_capacity"] == "true"]
    return prefilter, candidates


def review(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    decisions = {
        **{pair: ("accept", "") for pair in ACCEPTED_PAIRS},
        **{pair: ("reject", note) for pair, note in REJECTED_PAIRS.items()},
        **{pair: ("defer", note) for pair, note in DEFERRED_PAIRS.items()},
    }
    keys = {(row["chinese"], row["english"]) for row in candidates}
    if keys != set(decisions):
        raise SystemExit(
            "NAER education review coverage mismatch: "
            f"unreviewed={ascii(sorted(keys - set(decisions)))}; unexpected={ascii(sorted(set(decisions) - keys))}"
        )
    output = []
    for row in candidates:
        pair = (row["chinese"], row["english"])
        decision, note = decisions[pair]
        if decision == "accept":
            note = (
                "Accepted after review: the official education terminology entry has a coherent education, "
                "educational psychology, school administration, or learning sense matching the exact local "
                "ECDICT noun gloss, with local IPA and reachable pinyin."
            )
        output.append({**row, "decision": decision, "review_note": note})
    return output


def build(prefilter: list[dict[str, str]], candidates: list[dict[str, str]], reviewed: list[dict[str, str]], inputs: dict) -> dict:
    accepted = [row for row in reviewed if row["decision"] == "accept"]
    deferred = [row for row in reviewed if row["decision"] == "defer"]
    rejected = [row for row in reviewed if row["decision"] == "reject"]
    per_key: Counter[str] = Counter()
    expansion_rows = []
    for row in accepted:
        chinese, english = row["chinese"], row["english"]
        if (chinese, english) in inputs["pairs"] or chinese not in inputs["pinyin"]:
            raise SystemExit(f"Accepted NAER education mapping is already mapped or unreachable: {chinese} -> {english}")
        if inputs["extras"].get(chinese, 0) + per_key[chinese] >= 8:
            raise SystemExit(f"Accepted NAER education mapping exceeds per-key expansion limit: {chinese} -> {english}")
        per_key[chinese] += 1
        expansion_rows.append({"chinese": chinese, "english": english, "pos": "n.", "source": SOURCE})
    expansion_rows.sort(key=lambda row: (row["chinese"], row["english"]))

    exact_by_word: dict[str, list[dict[str, str]]] = {}
    for row in prefilter:
        exact_by_word.setdefault(row["english"], []).append(row)
    tag_rows = [{"english": word, "mask": str(EDUCATION_BIT), "source": SOURCE} for word in sorted(exact_by_word)]
    tag_review_rows = []
    for word, matching in sorted(exact_by_word.items()):
        tag_review_rows.append({
            "english": word,
            "source_records": ",".join(sorted({number for row in matching for number in row["source_records"].split(",")}, key=int)),
            "source_pairs": " | ".join(f"{row['chinese']} -> {word}" for row in matching),
            "already_education_tag": str(word in inputs["existing_education_words"]).lower(),
            "decision": "accept",
            "review_note": (
                "Accepted as an education-source membership: the headword occurs in the official NAER Education "
                "Terminology snapshot and has an exact local noun meaning, IPA, and reachable pinyin. This source "
                "membership does not imply that the word is education-specific in every sense."
            ),
        })
    for row in accepted:
        if row["english"] not in exact_by_word:
            raise SystemExit(f"Accepted education mapping lacks an education source-membership record: {row['english']}")

    outputs = {}
    outputs[PREFILTER.relative_to(DATA).as_posix()] = write_tsv(PREFILTER, PREFILTER_FIELDS, prefilter)
    outputs[CANDIDATES.relative_to(DATA).as_posix()] = write_tsv(CANDIDATES, PREFILTER_FIELDS, candidates)
    outputs[REVIEWED.relative_to(DATA).as_posix()] = write_tsv(REVIEWED, REVIEW_FIELDS, reviewed)
    outputs[TAG_REVIEWED.relative_to(DATA).as_posix()] = write_tsv(TAG_REVIEWED, TAG_FIELDS, tag_review_rows)
    outputs[EXPANSION.relative_to(DATA).as_posix()] = write_tsv(EXPANSION, ("chinese", "english", "pos", "source"), expansion_rows, header=False)
    outputs[TAGS.relative_to(DATA).as_posix()] = write_tsv(TAGS, ("english", "mask", "source"), tag_rows, header=False)

    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as stream:
        source_record_count = sum(1 for _ in csv.DictReader(stream))
    metadata = json.loads(SOURCE_METADATA.read_text(encoding="utf-8-sig"))
    manifest = {
        "batch": "35-naer-education-terminology",
        "source": {
            "title": "National Academy for Educational Research - Education Terminology",
            "provider": "National Academy for Educational Research",
            "dataset_id": "6319",
            "dataset_url": "https://data.gov.tw/en/datasets/6319",
            "resource_url": metadata["resource_url"],
            "license": "Open Government Data License v1.0",
            "license_url": "https://data.gov.tw/license",
            "portal_updated_at": metadata["portal_updated_at"],
            "snapshot_sha256": SOURCE_SHA256,
            "snapshot_bytes": SOURCE_CSV.stat().st_size,
            "records": source_record_count,
        },
        "filters": {
            "source_scope": "Single-word English entries with exact local ECDICT noun gloss, UK or US IPA, reachable local pinyin key, and local expansion capacity.",
            "candidate_scope": "Every previously unmapped eligible pair receives an explicit accept/reject/defer decision; only reviewed concise standalone mappings enter runtime data.",
            "education_tag_scope": "A word receives education-source membership only when it occurs in the official NAER Education Terminology snapshot and has exact local noun, IPA, and pinyin evidence; membership does not imply every sense is education-specific.",
            "traditional_to_simplified": "Traditional Chinese source terms are normalized using OpenCC t2s before matching.",
            "runtime_per_key_cap": 8,
        },
        "counts": {
            "source_records": source_record_count,
            "eligible_exact_pairs": len(prefilter),
            "already_mapped_pairs": sum(row["already_mapped"] == "true" for row in prefilter),
            "capacity_blocked_pairs": sum(row["already_mapped"] == "false" and row["spare_capacity"] == "false" for row in prefilter),
            "new_review_candidates": len(candidates),
            "accepted_mappings": len(accepted),
            "rejected_candidates": len(rejected),
            "deferred_candidates": len(deferred),
            "new_english_headwords": len({row["english"] for row in accepted if row["existing_headword"] == "false"}),
            "education_tag_source_memberships": len(tag_rows),
            "new_education_tag_memberships": len({row["english"] for row in tag_rows} - inputs["existing_education_words"]),
            "reviewed_tag_headwords": len(tag_review_rows),
        },
        "accepted_pairs": [f"{row['chinese']} -> {row['english']} (n.)" for row in accepted],
        "rejected_pairs": [{"pair": f"{row['chinese']} -> {row['english']}", "reason": row["review_note"]} for row in rejected],
        "deferred_pairs": [{"pair": f"{row['chinese']} -> {row['english']}", "reason": row["review_note"]} for row in deferred],
        "source_hashes": {
            SOURCE_CSV.name: SOURCE_SHA256,
            SOURCE_METADATA.name: sha(SOURCE_METADATA.read_bytes()),
            **inputs["runtime_hashes"],
        },
        "base_lexicon_hashes": inputs["hashes"],
        "outputs": {name: sha(payload) for name, payload in outputs.items()},
        "runtime_note": f"Only {len(expansion_rows)} reviewed mappings and {len(tag_rows)} education-membership rows enter the once-initialized offline lookup; the {source_record_count:,}-row source CSV is never read while typing.",
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    inputs = load_inputs()
    prefilter, candidates = discover(inputs)
    reviewed = review(candidates)
    manifest = build(prefilter, candidates, reviewed, inputs)
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
