"""Build a reviewed management-vocabulary tranche from pinned NAER open data."""
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
SOURCE_CSV = DATA / "sources/naer/management-academic-terms-2026-08-12.csv"
SOURCE_METADATA = DATA / "sources/naer/management-dataset.json"
SOURCE_SHA256 = "2f323ca6b4cf2a5a83dc01b1b044551c809e73f2f025858fd0b69c7b99e2bf4d"
PREFILTER = DATA / "batches/33-naer-management-prefilter.tsv"
CANDIDATES = DATA / "batches/33-naer-management-candidates.tsv"
REVIEWED = DATA / "batches/33-naer-management-reviewed.tsv"
TAG_REVIEWED = DATA / "batches/33-naer-management-tags-reviewed.tsv"
EXPANSION = DATA / "naer-management-expansion.tsv"
TAGS = DATA / "naer-management-tags.tsv"
MANIFEST = DATA / "naer-management-manifest.json"

SOURCE = "NAER Management Academic Terms OGDL v1.0"
BUSINESS_BIT = 1 << 7
WORD = re.compile(r"[a-z][a-z'-]*\Z")
VARIANT_SEPARATOR = re.compile(r"[；;、，,/／|]+")

PREFILTER_FIELDS = (
    "english", "chinese", "source_chinese", "source_records", "source_urls",
    "pinyin", "pinyin_frequency", "ipa_sources", "ecdict_exact_noun_glosses",
    "already_mapped", "existing_headword", "existing_business_tag", "spare_capacity",
)
REVIEW_FIELDS = PREFILTER_FIELDS + ("decision", "review_note")
TAG_FIELDS = ("english", "source_records", "source_pairs", "already_business_tag", "decision", "review_note")

# These decisions are restricted to pairs that have an exact NAER term, ECDICT
# noun gloss, local IPA, and an existing pinyin key. The remaining candidates
# are deliberately excluded for semantic mismatch or weak standalone value.
ACCEPTED_PAIRS = {
    ("聚合", "aggregation"),
    ("装配", "assembly"),
    ("保证", "assurance"),
    ("归因", "attribution"),
    ("官僚", "bureaucracy"),
    ("能力", "competence"),
    ("集中", "concentration"),
    ("公司", "corporation"),
    ("信条", "credo"),
    ("线索", "cues"),
    ("决策", "decision-making"),
    ("降职", "demotion"),
    ("支配", "domination"),
    ("环境", "environments"),
    ("评估", "evaluation"),
    ("交易所", "exchanges"),
    ("特征", "features"),
    ("检验", "inspection"),
    ("介入", "intervention"),
    ("负债", "liabilities"),
    ("忠诚", "loyalty"),
    ("管理", "management"),
    ("行销", "marketing"),
    ("新奇", "novelty"),
    ("目的", "objective"),
    ("组织", "organization"),
    ("透支", "overdrafts"),
    ("定位", "positioning"),
    ("条款", "provision"),
    ("委托书", "proxy"),
    ("处罚", "punishment"),
    ("惩罚", "punishment"),
    ("合理化", "rationalization"),
    ("辞职", "resignation"),
    ("资源", "resources"),
    ("惯例", "routine"),
    ("怠工", "sabotage"),
    ("压力", "stress"),
    ("接管", "takeovers"),
    ("威胁", "threats"),
    ("批发", "wholesaling"),
}
REJECTED_PAIRS = {
    ("分类", "assortment"): "The source term means a selection or range; 分类 is classification and is not a reliable standalone equivalent.",
    ("引用", "citation"): "This is a generic research-reference sense; the record does not establish a useful management-specific mapping.",
    ("朽木", "deadwood"): "The literal Chinese gloss is idiomatic and misleading as a practical standalone translation of this English term.",
    ("扩充", "extension"): "The local gloss is too broad to establish a management-specific sense.",
    ("旋转", "revolution"): "The exact local gloss is a mechanical rotation sense, outside the management term represented by this batch.",
}
DEFERRED_PAIRS = {
    ("迁移", "transfer"): "The source and local gloss are individually exact, but 迁移 can mean migration or transfer in several unrelated fields; defer until a narrower management context is available.",
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
        raise SystemExit("Pinned NAER management CSV SHA-256 mismatch")
    metadata_bytes = SOURCE_METADATA.read_bytes()
    metadata = json.loads(metadata_bytes.decode("utf-8-sig"))
    if metadata.get("dataset_id") != "15440" or metadata.get("snapshot_sha256") != SOURCE_SHA256:
        raise SystemExit("Unexpected NAER management dataset metadata")

    sys.path.insert(0, str(ROOT / "scripts"))
    import build_finance_i18n_batch as finance_batch

    inputs = finance_batch.load_inputs()
    runtime_source = (ROOT / "vocabulary/src/expansion/mod.rs").read_text(encoding="utf-8")
    compiled = set(re.findall(r'include_str!\("../../data/([^" ]+\.tsv)"\)', runtime_source))
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
    tag_files = sorted(set(re.findall(r'include_str!\("\.\./data/([^" ]+-tags\.tsv)"\)', lib_source)) - {TAGS.name})
    business_words = set()
    for filename in tag_files:
        for line in (DATA / filename).read_text(encoding="utf-8").splitlines():
            fields = line.split("\t")
            if not fields:
                continue
            for field in fields[1:]:
                if field.isdigit() and int(field) & BUSINESS_BIT:
                    business_words.add(fields[0].casefold())
                    break
    inputs["existing_business_words"] = business_words
    return inputs


def discover(inputs: dict) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    grouped: dict[tuple[str, str], dict] = {}
    ipa_words = inputs["uk"] | inputs["us"]
    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        expected = ("序號", "英文名稱", "中文名稱", "中國大陸譯名", "來源網站")
        if tuple(reader.fieldnames or ()) != expected:
            raise SystemExit(f"Unexpected NAER management CSV columns: {reader.fieldnames}")
        for row in reader:
            english = row["英文名稱"].strip().casefold().strip("()")
            if not WORD.fullmatch(english) or english not in ipa_words:
                continue
            noun_glosses = sorted({gloss for gloss, pos in inputs["ecdict"].get(english, ()) if pos == "n."})
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
        extras = inputs["extras"].get(chinese, 0)
        prefilter.append({
            "english": english,
            "chinese": chinese,
            "source_chinese": " | ".join(sorted(evidence["source_chinese"])),
            "source_records": ",".join(sorted(evidence["rows"], key=int)),
            "source_urls": " | ".join(sorted(evidence["source_urls"])),
            "pinyin": pinyin,
            "pinyin_frequency": str(frequency),
            "ipa_sources": ",".join(name for name, words in (("UK", inputs["uk"]), ("US", inputs["us"])) if english in words),
            "ecdict_exact_noun_glosses": " | ".join(sorted({g for g, pos in inputs["ecdict"].get(english, ()) if pos == "n." and g == chinese})),
            "already_mapped": str((chinese, english) in inputs["pairs"]).lower(),
            "existing_headword": str(english in inputs["words"]).lower(),
            "existing_business_tag": str(english in inputs["existing_business_words"]).lower(),
            "spare_capacity": str(extras < 8).lower(),
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
            "NAER management review coverage mismatch: "
            f"unreviewed={sorted(keys - set(decisions))}; unexpected={sorted(set(decisions) - keys)}"
        )
    rows = []
    for row in candidates:
        decision, note = decisions[(row["chinese"], row["english"])]
        if decision == "accept":
            note = "Accepted after review: the NAER management term, exact local ECDICT noun gloss, and available pinyin/IPA support a coherent standalone management or business sense."
        rows.append({**row, "decision": decision, "review_note": note})
    return rows


def build(prefilter: list[dict[str, str]], candidates: list[dict[str, str]], reviewed: list[dict[str, str]], inputs: dict) -> dict:
    accepted = [row for row in reviewed if row["decision"] == "accept"]
    rejected = [row for row in reviewed if row["decision"] == "reject"]
    deferred = [row for row in reviewed if row["decision"] == "defer"]
    per_key: Counter[str] = Counter()
    expansion_rows = []
    for row in accepted:
        chinese, english = row["chinese"], row["english"]
        if (chinese, english) in inputs["pairs"] or chinese not in inputs["pinyin"]:
            raise SystemExit(f"Accepted NAER management mapping is already mapped or unreachable: {chinese} -> {english}")
        if inputs["extras"].get(chinese, 0) + per_key[chinese] >= 8:
            raise SystemExit(f"Accepted NAER management mapping exceeds per-key expansion limit: {chinese} -> {english}")
        per_key[chinese] += 1
        expansion_rows.append({"chinese": chinese, "english": english, "pos": "n.", "source": SOURCE})
    expansion_rows.sort(key=lambda row: (row["chinese"], row["english"]))

    exact_by_word: dict[str, list[dict[str, str]]] = {}
    for row in prefilter:
        exact_by_word.setdefault(row["english"], []).append(row)
    tag_rows = [{"english": word, "mask": str(BUSINESS_BIT), "source": SOURCE} for word in sorted(exact_by_word)]
    tag_review_rows = []
    for word, matching in sorted(exact_by_word.items()):
        tag_review_rows.append({
            "english": word,
            "source_records": ",".join(sorted({n for row in matching for n in row["source_records"].split(",")}, key=int)),
            "source_pairs": " | ".join(f"{row['chinese']} -> {word}" for row in matching),
            "already_business_tag": str(word in inputs["existing_business_words"]).lower(),
            "decision": "accept",
            "review_note": "The English headword is explicitly present in the official NAER Management Academic Terms snapshot; local exact noun meaning, IPA, and pinyin evidence are present. The source term-list membership supplies the business-domain classification.",
        })
    for row in accepted:
        if row["english"] not in exact_by_word:
            raise SystemExit(f"Accepted management mapping has no reviewed business membership: {row['english']}")

    prefilter_bytes = write_tsv(PREFILTER, PREFILTER_FIELDS, prefilter)
    candidate_bytes = write_tsv(CANDIDATES, PREFILTER_FIELDS, candidates)
    reviewed_bytes = write_tsv(REVIEWED, REVIEW_FIELDS, reviewed)
    tag_review_bytes = write_tsv(TAG_REVIEWED, TAG_FIELDS, tag_review_rows)
    expansion_bytes = write_tsv(EXPANSION, ("chinese", "english", "pos", "source"), expansion_rows, header=False)
    tags_bytes = write_tsv(TAGS, ("english", "mask", "source"), tag_rows, header=False)

    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as stream:
        source_record_count = sum(1 for _ in csv.DictReader(stream))
    manifest = {
        "batch": "33-naer-management-terms",
        "source": {
            "title": "National Academy for Educational Research - Management Academic Terms",
            "provider": "National Academy for Educational Research",
            "dataset_id": "15440",
            "dataset_url": "https://data.gov.tw/dataset/15440",
            "resource_url": "https://opendata.naer.edu.tw/學術名詞/國家教育研究院-管理學學術名詞.csv",
            "license": "Open Government Data License v1.0",
            "license_url": "https://data.gov.tw/license",
            "portal_updated_at": "2026-08-12 13:43",
            "snapshot_sha256": SOURCE_SHA256,
            "snapshot_bytes": SOURCE_CSV.stat().st_size,
            "records": source_record_count,
        },
        "filters": {
            "source_scope": "One-word English entries with exact local ECDICT noun gloss, UK or US IPA, reachable local pinyin key, and local expansion capacity.",
            "candidate_scope": "Every previously unmapped eligible pair receives an explicit accept/reject/defer decision; only reviewed concise standalone terms enter runtime data.",
            "business_tag_scope": "An exact locally verifiable English headword is tagged business when explicitly present in the NAER Management Academic Terms source; source membership is the domain evidence.",
            "traditional_to_simplified": "OpenCC t2s",
            "runtime_per_key_cap": 8,
        },
        "counts": {
            "source_records": source_record_count,
            "eligible_exact_pairs": len(prefilter),
            "already_mapped_pairs": sum(row["already_mapped"] == "true" for row in prefilter),
            "new_review_candidates": len(candidates),
            "accepted_mappings": len(accepted),
            "rejected_candidates": len(rejected),
            "deferred_candidates": len(deferred),
            "new_english_headwords": len({row["english"] for row in accepted if row["existing_headword"] == "false"}),
            "business_tag_source_memberships": len(tag_rows),
            "new_business_tag_memberships": len({row["english"] for row in tag_rows} - inputs["existing_business_words"]),
            "reviewed_tag_headwords": len(tag_review_rows),
        },
        "accepted_pairs": [f"{row['chinese']} -> {row['english']} (n.)" for row in accepted],
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
        "runtime_note": "Only reviewed compact mappings and business membership rows enter offline lookup; the 12,936-row source CSV is never read while typing.",
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
            "rejected": sum(row["decision"] == "reject" for row in reviewed),
            "deferred": sum(row["decision"] == "defer" for row in reviewed),
        }, ensure_ascii=False, indent=2))
        return
    manifest = build(prefilter, candidates, reviewed, inputs)
    print(json.dumps(manifest["counts"], ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
