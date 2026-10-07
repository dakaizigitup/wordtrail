"""Build a reviewed economics vocabulary tranche from pinned NAER open data."""
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
SOURCE_CSV = DATA / "sources/naer/economics-academic-terms-2025-12-16.csv"
SOURCE_METADATA = DATA / "sources/naer/economics-dataset.json"
SOURCE_SHA256 = "6c6f605a05ed30c9c11dadd1df5a4de3d7ca621a49b70f64669a847fc6d1eea9"
SOURCE_METADATA_SHA256 = "d14fa535290104a9ec91a67a76f649682ca12457682f8e19b365219cf6f0bbf3"
PREFILTER = DATA / "batches/30-naer-economics-prefilter.tsv"
CANDIDATES = DATA / "batches/30-naer-economics-candidates.tsv"
REVIEWED = DATA / "batches/30-naer-economics-reviewed.tsv"
EXPANSION = DATA / "naer-economics-expansion.tsv"
TAGS = DATA / "naer-economics-tags.tsv"
MANIFEST = DATA / "naer-economics-manifest.json"

SOURCE = "NAER Economics Academic Terms OGDL v1.0"
BUSINESS_BIT = 1 << 7
WORD = re.compile(r"[a-z][a-z'-]*\Z")
VARIANT_SEPARATOR = re.compile(r"[；;、，,/／|]+")

PREFILTER_FIELDS = (
    "english", "chinese", "source_chinese", "source_records", "source_url_field",
    "pinyin", "pinyin_frequency", "ipa_sources", "ecdict_exact_noun_glosses",
    "already_mapped", "existing_headword", "existing_business_tag", "spare_capacity",
)
REVIEW_FIELDS = PREFILTER_FIELDS + ("decision", "review_note")

# Keep only concise, useful economic, financial, labor, or commercial senses.
ACCEPTED = {
    ("旷工", "absenteeism"): "The official economics glossary and ECDICT agree on 旷工; this is a labor-economics and workplace term.",
    ("谈判", "bargaining"): "The source lists bargaining with 谈判; this is a standard negotiation and labor-economics concept.",
    ("泡沫", "bubbles"): "The official economics glossary uses 泡沫 for the market-bubble sense; ECDICT and local IPA confirm the plural headword.",
    ("佣金", "commissions"): "The source and ECDICT agree on 佣金; this is a direct commercial payment term.",
    ("竞争", "competition"): "竞争 is the exact, central market-economics sense in both the source and ECDICT.",
    ("消费", "consumption"): "消费 is an exact core economics term in the source and ECDICT.",
    ("收敛", "convergence"): "The source and ECDICT agree on 收敛; economic convergence is a standard technical sense.",
    ("协调", "coordination"): "The official economics entry gives 协调; this is a useful market and organizational economics sense.",
    ("公司", "corporations"): "The source and ECDICT agree on 公司; this is a direct commercial headword with local IPA.",
    ("扭曲", "distortion"): "The source and ECDICT agree on 扭曲; market distortion is a standard economic sense.",
    ("侵占", "embezzlement"): "The source and ECDICT support 侵占; this is a relevant business-fraud and financial-law term.",
    ("执行", "enforcement"): "The source lists enforcement as 执行/强制执行; the exact local ECDICT noun gloss is 执行, relevant to economic regulation.",
    ("均衡", "equilibrium"): "均衡 is the direct and central market-economics sense in the source and ECDICT.",
    ("诱因", "incentives"): "The source and ECDICT agree on 诱因; incentives are a core economics concept.",
    ("补偿", "indemnity"): "The source and ECDICT agree on 补偿; this is a direct insurance and contract term.",
    ("创新", "innovation"): "The official glossary and ECDICT agree on 创新; economic and business innovation is a standard sense.",
    ("清算", "liquidation"): "清算 is the exact financial and insolvency sense in the source and ECDICT.",
    ("调解", "mediation"): "The official source and ECDICT agree on 调解; commercial and labor dispute mediation is a useful professional term.",
    ("合并", "merger"): "合并 is the exact business-combination sense in the source and ECDICT.",
    ("流动性", "mobility"): "The source and ECDICT agree on 流动性; this is the factor/labor-mobility sense used in economics.",
    ("有价证券", "securities"): "The source and ECDICT agree on 有价证券; this is an exact financial-market term.",
    ("转包", "subcontracting"): "The source and ECDICT agree on 转包; this is a direct commercial and procurement term.",
    ("补助", "subsidization"): "The source and ECDICT agree on 补助; subsidization is a direct public-economics term.",
    ("保证", "surety"): "The source lists 保證/擔保 and ECDICT confirms 保证; surety is a direct financial/legal guarantee sense.",
    ("剩余", "surplus"): "The source and ECDICT agree on 剩余; this is a standard supply, trade, and market-economics term.",
    ("纺织品", "textiles"): "纺织品 is the exact source and ECDICT noun gloss; this is a useful trade and industry term.",
    ("运输", "transportation"): "The source and ECDICT agree on 运输; this is a direct economic-sector and logistics term.",
    ("保证", "warranty"): "The source and ECDICT agree on 保证; warranty is a commercial contract and consumer-protection term.",
}

REJECTED = {
    ("剥夺", "divestiture"): "The English term means disposal of an asset or business interest; 剥夺 is not a suitable standalone translation.",
    ("复制", "reproduction"): "In economics reproduction means social/economic reproduction, not copying; the source gloss is misleading without that phrase context.",
    ("冷冻", "refrigeration"): "This is a technical cooling sense, not a useful business/economics vocabulary mapping.",
    ("踏板", "treadle"): "The word is unrelated to economics or business in this source context.",
    ("踏车", "treadmill"): "The word is unrelated to economics or business in this source context.",
    ("监禁", "imprisonment"): "This is a general legal/criminal term, not a suitable business vocabulary entry here.",
    ("庇护", "asylum"): "This is a general legal/social term, not a suitable business vocabulary entry here.",
    ("技工", "craftsman"): "This is an occupation label rather than a useful business/economics translation in this tranche.",
    ("技术", "technique"): "This is a broad general meaning; the source does not establish a distinct economics sense.",
    ("努力", "effort"): "This is a broad general meaning with no sufficiently specific economics sense for the business tag.",
    ("学习", "learning"): "This is a broad general meaning; the source does not establish a distinct economics sense.",
    ("失败", "failure"): "This is a broad general meaning; a phrase such as market failure is needed for the economic sense.",
}

BUSINESS_TAG_FILES = (
    "professional-domain-tags.tsv", "cjk-compsci-tags.tsv", "fibo-business-tags.tsv",
    "better-quant-business-tags.tsv", "cfpb-finance-tags.tsv", "finance-i18n-tags.tsv",
)


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
        raise SystemExit("Pinned NAER economics CSV SHA-256 mismatch")
    metadata_bytes = SOURCE_METADATA.read_bytes()
    if sha(metadata_bytes) != SOURCE_METADATA_SHA256:
        raise SystemExit("Pinned NAER economics metadata SHA-256 mismatch")
    metadata = json.loads(metadata_bytes.decode("utf-8-sig"))
    if metadata.get("dataset_id") != "15405" or metadata.get("snapshot_sha256") != SOURCE_SHA256:
        raise SystemExit("Unexpected NAER economics dataset metadata")

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
    business_words = set()
    for filename in BUSINESS_TAG_FILES:
        for line in (DATA / filename).read_text(encoding="utf-8").splitlines():
            fields = line.split("\t")
            if len(fields) >= 2 and int(fields[1]) & BUSINESS_BIT:
                business_words.add(fields[0].casefold())
    inputs["existing_business_words"] = business_words
    return inputs


def discover(inputs: dict) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    grouped: dict[tuple[str, str], dict] = {}
    ipa_words = inputs["uk"] | inputs["us"]
    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        expected = ("序號", "英文名稱", "中文名稱", "來源網站")
        if tuple(reader.fieldnames or ()) != expected:
            raise SystemExit(f"Unexpected NAER economics CSV columns: {reader.fieldnames}")
        for row in reader:
            english = row["英文名稱"].strip().casefold().strip("()")
            if not WORD.fullmatch(english) or english not in ipa_words:
                continue
            noun_glosses = sorted({
                gloss for gloss, pos in inputs["ecdict"].get(english, ()) if pos == "n."
            })
            if not noun_glosses:
                continue
            for raw_chinese in VARIANT_SEPARATOR.split(row["中文名稱"].strip()):
                chinese = inputs["converter"].convert(raw_chinese.strip()).strip()
                if not chinese or chinese not in inputs["pinyin"] or chinese not in noun_glosses:
                    continue
                pair = (chinese, english)
                record = grouped.setdefault(pair, {"rows": set(), "source_chinese": set(), "source_urls": set()})
                record["rows"].add(row["序號"].strip())
                record["source_chinese"].add(row["中文名稱"].strip())
                record["source_urls"].add(row["來源網站"].strip())

    rows = []
    for (chinese, english), evidence in grouped.items():
        pinyin, frequency = inputs["pinyin"][chinese]
        rows.append({
            "english": english,
            "chinese": chinese,
            "source_chinese": " | ".join(sorted(evidence["source_chinese"])),
            "source_records": ",".join(sorted(evidence["rows"], key=int)),
            "source_url_field": " | ".join(sorted(evidence["source_urls"])),
            "pinyin": pinyin,
            "pinyin_frequency": str(frequency),
            "ipa_sources": ",".join(name for name, words in (("UK", inputs["uk"]), ("US", inputs["us"])) if english in words),
            "ecdict_exact_noun_glosses": " | ".join(sorted({g for g, pos in inputs["ecdict"].get(english, ()) if pos == "n."})),
            "already_mapped": str((chinese, english) in inputs["pairs"]).lower(),
            "existing_headword": str(english in inputs["words"]).lower(),
            "existing_business_tag": str(english in inputs["existing_business_words"]).lower(),
            "spare_capacity": str(inputs["extras"].get(chinese, 0) < 8).lower(),
        })
    rows.sort(key=lambda row: (row["english"], row["chinese"], row["source_records"]))
    candidates = [row for row in rows if row["already_mapped"] == "false" and row["spare_capacity"] == "true"]
    return rows, candidates


def review(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    reviewed = []
    for row in candidates:
        key = (row["chinese"], row["english"])
        if key in ACCEPTED:
            decision, note = "accept", ACCEPTED[key]
        elif key in REJECTED:
            decision, note = "reject", REJECTED[key]
        else:
            decision = "defer"
            note = "Passed exact noun, local IPA, exact pinyin, and capacity checks, but this isolated sense is broad or insufficiently specific for the business category; keep it out of runtime data pending stronger context."
        reviewed.append({**row, "decision": decision, "review_note": note})
    found_accepts = {(row["chinese"], row["english"]) for row in reviewed if row["decision"] == "accept"}
    missing = set(ACCEPTED) - found_accepts
    if missing:
        raise SystemExit(f"Curated NAER economics decisions absent from candidates: {sorted(missing)}")
    if len(found_accepts) != len(ACCEPTED):
        raise SystemExit("Unexpected accepted NAER economics pair")
    return reviewed


def build(prefilter: list[dict[str, str]], candidates: list[dict[str, str]], reviewed: list[dict[str, str]], inputs: dict) -> dict:
    accepted = [row for row in reviewed if row["decision"] == "accept"]
    rejected = [row for row in reviewed if row["decision"] == "reject"]
    deferred = [row for row in reviewed if row["decision"] == "defer"]
    per_key: Counter[str] = Counter()
    expansion_rows = []
    for row in accepted:
        chinese, english = row["chinese"], row["english"]
        if (chinese, english) in inputs["pairs"] or chinese not in inputs["pinyin"]:
            raise SystemExit(f"Accepted NAER economics mapping is already mapped or unreachable: {chinese} -> {english}")
        if inputs["extras"].get(chinese, 0) + per_key[chinese] >= 8:
            raise SystemExit(f"Accepted NAER economics mapping exceeds per-key expansion limit: {chinese} -> {english}")
        per_key[chinese] += 1
        expansion_rows.append({"chinese": chinese, "english": english, "pos": "n.", "source": SOURCE})
    expansion_rows.sort(key=lambda row: (row["chinese"], row["english"]))
    tag_words = sorted({row["english"] for row in accepted})
    tag_rows = [{"english": word, "mask": str(BUSINESS_BIT), "source": SOURCE} for word in tag_words]
    prefilter_bytes = write_tsv(PREFILTER, PREFILTER_FIELDS, prefilter)
    candidate_bytes = write_tsv(CANDIDATES, PREFILTER_FIELDS, candidates)
    reviewed_bytes = write_tsv(REVIEWED, REVIEW_FIELDS, reviewed)
    expansion_bytes = write_tsv(EXPANSION, ("chinese", "english", "pos", "source"), expansion_rows, header=False)
    tags_bytes = write_tsv(TAGS, ("english", "mask", "source"), tag_rows, header=False)
    source_hashes = {
        SOURCE_CSV.name: SOURCE_SHA256,
        SOURCE_METADATA.name: sha(SOURCE_METADATA.read_bytes()),
        **inputs["runtime_hashes"],
    }
    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as stream:
        source_record_count = sum(1 for _ in csv.DictReader(stream))
    manifest = {
        "batch": "30-naer-economics-terms",
        "source": {
            "title": "National Academy for Educational Research - Economics Terminology",
            "provider": "National Academy for Educational Research",
            "dataset_url": "https://data.gov.tw/en/datasets/15405",
            "resource_url": "https://opendata.naer.edu.tw/學術名詞/國家教育研究院-經濟學學術名詞.csv",
            "license": "Open Government Data License v1.0",
            "license_url": "https://data.gov.tw/license",
            "portal_updated_at": "2025-12-16 07:51",
            "snapshot_sha256": SOURCE_SHA256,
            "snapshot_bytes": SOURCE_CSV.stat().st_size,
        },
        "filters": {
            "source_scope": "One-word English glossary terms with local IPA, exact ECDICT noun gloss, exact pinyin key, and per-key expansion capacity.",
            "candidate_scope": "Previously unmapped pairs receive explicit accept/reject/defer decisions; only concise reviewed economic, finance, labor, or commercial senses ship.",
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
            "new_english_headwords": sum(row["existing_headword"] == "false" for row in accepted),
            "new_business_tag_memberships": len(set(tag_words) - inputs["existing_business_words"]),
        },
        "accepted_pairs": [f"{row['chinese']} -> {row['english']} (n.)" for row in accepted],
        "source_hashes": source_hashes,
        "base_lexicon_hashes": inputs["hashes"],
        "outputs": {
            PREFILTER.name: sha(prefilter_bytes),
            CANDIDATES.name: sha(candidate_bytes),
            REVIEWED.name: sha(reviewed_bytes),
            EXPANSION.name: sha(expansion_bytes),
            TAGS.name: sha(tags_bytes),
        },
        "runtime_note": "Only reviewed compact mappings and business membership rows enter the offline lookup; the source CSV is never scanned during typing.",
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
            "accepted_keys_missing": sorted(set(ACCEPTED) - {(row["chinese"], row["english"]) for row in candidates}),
        }, ensure_ascii=False, indent=2))
        return
    manifest = build(prefilter, candidates, reviewed, inputs)
    print(json.dumps(manifest["counts"], ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
