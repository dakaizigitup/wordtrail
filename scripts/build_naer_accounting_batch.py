"""Build a reviewed accounting vocabulary tranche from pinned NAER open data."""
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
SOURCE_CSV = DATA / "sources/naer/accounting-academic-terms-2026-08-12.csv"
SOURCE_METADATA = DATA / "sources/naer/accounting-dataset.json"
SOURCE_SHA256 = "46eaea4143811919253f94cd86062dcd49a9376bbe8ee85ac8c514a5d00a9869"
SOURCE_METADATA_SHA256 = "ad091b408312ab0b0817cea35befed96f70fd095ac4ac0d159ae7424da357f27"
PREFILTER = DATA / "batches/32-naer-accounting-prefilter.tsv"
CANDIDATES = DATA / "batches/32-naer-accounting-candidates.tsv"
REVIEWED = DATA / "batches/32-naer-accounting-reviewed.tsv"
TAG_REVIEWED = DATA / "batches/32-naer-accounting-tags-reviewed.tsv"
EXPANSION = DATA / "naer-accounting-expansion.tsv"
TAGS = DATA / "naer-accounting-tags.tsv"
MANIFEST = DATA / "naer-accounting-manifest.json"

SOURCE = "NAER Accounting Academic Terms OGDL v1.0"
BUSINESS_BIT = 1 << 7
WORD = re.compile(r"[a-z][a-z'-]*\Z")
VARIANT_SEPARATOR = re.compile(r"[；;、，,/／|]+")

PREFILTER_FIELDS = (
    "english", "chinese", "source_chinese", "source_records", "source_url_field",
    "pinyin", "pinyin_frequency", "ipa_sources", "ecdict_exact_noun_glosses",
    "already_mapped", "existing_headword", "existing_business_tag", "spare_capacity",
)
REVIEW_FIELDS = PREFILTER_FIELDS + ("decision", "review_note")

# Mapping decisions below were curated from the pinned source candidate report.
ACCEPTED: dict[tuple[str, str], str] = {
    ("商业", "business"): "The source and ECDICT give the exact noun sense 商业; this is a useful core business term.",
    ("合并", "combination"): "The source explicitly pairs combination with 合并; business combination is a standard accounting concept.",
    ("交货", "delivery"): "Delivery is directly relevant to inventory, sales, and revenue recognition; 交货 is the exact local noun gloss.",
    ("解散", "dissolution"): "Dissolution of an entity is a standard corporate and accounting event; 解散 is exact.",
    ("财产", "estate"): "Estate is a property/accounting concept, and 财产 is the exact source and local gloss.",
    ("汇兑", "exchange"): "Exchange in this glossary has a foreign-currency/accounting use; 汇兑 is an exact local noun gloss.",
    ("商号", "firm"): "Firm denotes a business entity; 商号 is the exact source and local noun gloss.",
    ("资金", "fund"): "Fund is a core business and accounting noun; 资金 is the exact local gloss and a distinct sense from 基金.",
    ("收益", "income"): "Income is a core accounting concept; 收益 is an exact source and local noun gloss.",
    ("差额", "margin"): "Margin is a recognized financial/accounting measure; 差额 is an exact source and local noun gloss.",
    ("到期", "maturity"): "Maturity applies to loans and securities; 到期 is an exact financial-accounting gloss.",
    ("支出", "outgo"): "Outgo is an accounting expenditure term; 支出 is the exact source and local noun gloss.",
    ("合伙", "partnership"): "Partnership is a standard business entity and accounting topic; 合伙 is exact.",
    ("专利权", "patent"): "A patent is an identifiable intangible asset; 专利权 is the exact source and local noun gloss.",
    ("准备", "provision"): "Provision is a standard accounting liability/expense concept; 准备 is the exact source and local noun gloss.",
    ("价目", "quotations"): "Quotations are price offers used in commercial transactions; 价目 is an exact source and local noun gloss.",
    ("实现", "realization"): "Realization is an accounting recognition concept; 实现 is the exact source and local noun gloss.",
    ("折扣", "rebate"): "Rebate is a commercial price adjustment; 折扣 is an exact source and local noun gloss.",
    ("收入", "receipt"): "The source uses receipt in the accounting sense of money received; 收入 is an exact local noun gloss.",
    ("改组", "reorganization"): "Reorganization is a recognized business restructuring event; 改组 is exact.",
    ("收入", "revenue"): "Revenue is a core accounting concept; 收入 is the exact source and local noun gloss.",
    ("出纳员", "treasurer"): "Treasurer is an accounting/finance role; 出纳员 is an exact source and local noun gloss.",
}
REJECTED: dict[tuple[str, str], str] = {
    ("容器", "containers"): "Containers are not an accounting term in this isolated source sense; the gloss is more likely a physical container.",
    ("本金", "corpus"): "Corpus normally means a body of texts or a principal fund in specialized contexts; 本金 is too ambiguous without that phrase context.",
    ("扩充", "expansion"): "This is a broad general sense without a sufficiently specific accounting meaning.",
    ("扩充", "extension"): "This is a broad general sense without a sufficiently specific accounting meaning.",
    ("独立", "independence"): "The isolated translation is too broad to serve as a useful accounting mapping.",
    ("标志", "label"): "The source/local gloss is generic and does not establish an accounting-specific use.",
    ("落后", "lag"): "This is a general sense rather than a useful accounting term.",
    ("动作", "operation"): "动作 is not an appropriate standalone accounting translation of operation.",
    ("零件", "parts"): "This is a physical-parts sense and not a reliable accounting term without inventory context.",
    ("排列", "permutation"): "This is a mathematical sense, not an accounting use.",
    ("利益", "profit"): "利益 is broader than profit; the established accounting translation is 利润, so this mapping would mislead.",
    ("法令", "ordinance"): "This is a legal sense without a sufficiently specific accounting use.",
}

# Only exact, locally verifiable headwords with a direct accounting or
# commercial use receive the shared business target.
ACCOUNTING_TAG_TERMS = (
    "accountant adjustment allotment allowance annuity asset assignment audit balance basis beneficiary bequest bill bond bonus bookkeeping budget business byproduct capital cash cashier chart chattel check client commission combination consolidation convention copyright credit creditor cycle debit debt debtor default delivery deposit depreciation disbursement discount dissolution distribution dividend draft embezzlement entrepreneur equipment error estate exchange expense firm fuel fund goods guarantor income indenture inflation interest investment invoice item job liquidation loss material margin maturity merchandise money mortgage note obligation outgo ownership overdraft partnership patent principal principle product productivity production profit property project provision quotations ratio realization rebate receipt redemption remittance rent reorganization repair report representation reserve responsibility retirement revenue sample specie spoilage standard stock stockholder surplus surtax terms title total transaction transfer transportation treasurer trustee turnover valuation value variable vendee vendor voucher wages warranty withdrawal"
).split()
TAG_ACCEPTED = {
    word: (
        "The pinned NAER accounting glossary explicitly lists this headword with an exact local Chinese gloss; "
        "local pinyin, IPA, and ECDICT noun evidence are present, and the term has a direct accounting or commercial use."
    )
    for word in ACCOUNTING_TAG_TERMS
}
TAG_REJECTED = {
    "axiom": "This is a general logic/mathematics term; the source record does not establish a useful accounting or commercial sense.",
    "coefficient": "This is a mathematics/statistics term without a sufficiently direct accounting use in the source entry.",
    "concept": "This is too broad to be a useful accounting target headword.",
    "constant": "The local exact gloss is a general mathematical sense; the source entry does not establish a distinct accounting concept.",
    "corpus": "This is a text-corpus or context-specific sense, not a useful standalone accounting term.",
    "expansion": "This is a broad general sense with no accounting-specific evidence in the source row.",
    "extension": "This is a broad general sense with no accounting-specific evidence in the source row.",
    "independence": "This is a general concept and not a sufficiently specific accounting/commercial headword.",
    "inequality": "This is a mathematical concept without a direct accounting use in the source entry.",
    "information": "This is too broad to be a useful accounting target headword.",
    "integer": "This is a data/mathematics term rather than an accounting term in the source sense.",
    "label": "The exact local meaning is a generic sign/label, not a useful accounting concept.",
    "lag": "This is a broad timing sense and is not a sufficiently specific accounting term.",
    "manual": "This is a general book/instruction sense without a distinct accounting use in the source entry.",
    "norm": "This is a broad standard/norm sense, not a useful accounting term here.",
    "operation": "The source pairs this with the generic Chinese gloss 动作; this does not establish an accounting operation sense.",
    "ordinance": "This is a general legal instrument, not a sufficiently specific accounting concept.",
    "parameter": "This is a general mathematical/modeling term without a direct accounting use in the source row.",
    "permutation": "This is a mathematical term and not an accounting headword in the source context.",
    "priority": "This is too broad to be a useful accounting target headword.",
    "progression": "This is a mathematical/general sequence sense without an accounting-specific use.",
    "proxy": "This is a general representation/substitute sense, not a useful accounting term here.",
    "random": "This is a general statistical descriptor and not a sufficiently specific accounting term.",
    "resource": "This is too broad to establish an accounting-specific headword in this source row.",
    "ruling": "This is a general legal decision rather than an accounting term in the source sense.",
    "specification": "This is a broad technical description sense, not a useful accounting headword here.",
    "speculator": "This is an occupation/market participant, but the source entry does not establish a direct accounting concept.",
    "stub": "This is a fragment/short stub sense and not a useful accounting headword in this source context.",
    "tool": "This is a generic object and not an accounting-specific headword.",
    "utility": "The source's exact gloss 公用事业 is an industry/economic sense, not an accounting-specific use.",
    "will": "This is a general legal/inheritance document, not a sufficiently direct accounting term for this target.",
}
TAG_DEFERRED = {
    "assembly": "Could refer to a physical assembly or a company meeting; the source row and exact gloss do not resolve the intended commercial sense.",
    "charter": "May refer to a company charter, but the local gloss 执照 also has broad legal meanings; defer the category tag.",
    "containers": "Could refer to inventory/shipping containers, but the standalone gloss does not establish the accounting context.",
    "demand": "A relevant economics/marketing word, but its accounting-specific use is unclear from the isolated source row.",
    "increment": "Could be a value or cost increment, but the source row does not identify the accounting context.",
    "lapse": "Could refer to a lapsed financial/insurance contract, but the source row does not distinguish that from the general sense.",
    "objective": "Accounting has formal objectives, but the source row and gloss are too general to confirm that use.",
    "parts": "Could refer to inventory components, but the source row does not establish whether this means accounting inventory or physical parts.",
    "program": "Could refer to a budget/program accounting concept, but the isolated source row is too broad.",
    "system": "Could mean an accounting information system, but the source row does not establish that technical sense.",
}

BUSINESS_TAG_FILES = (
    "professional-domain-tags.tsv", "cjk-compsci-tags.tsv", "fibo-business-tags.tsv",
    "better-quant-business-tags.tsv", "cfpb-finance-tags.tsv", "finance-i18n-tags.tsv",
    "naer-economics-tags.tsv",
)

TAG_FIELDS = ("english", "source_records", "source_pairs", "already_business_tag", "decision", "review_note")


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
        raise SystemExit("Pinned NAER accounting CSV SHA-256 mismatch")
    metadata_bytes = SOURCE_METADATA.read_bytes()
    if sha(metadata_bytes) != SOURCE_METADATA_SHA256:
        raise SystemExit("Pinned NAER accounting metadata SHA-256 mismatch")
    metadata = json.loads(metadata_bytes.decode("utf-8-sig"))
    if metadata.get("dataset_id") != "15404" or metadata.get("snapshot_sha256") != SOURCE_SHA256:
        raise SystemExit("Unexpected NAER accounting dataset metadata")

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
            raise SystemExit(f"Unexpected NAER accounting CSV columns: {reader.fieldnames}")
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
            note = "Passed exact noun, local IPA, exact pinyin, and capacity checks, but the standalone sense or accounting relevance needs additional review; keep it out of runtime data for now."
        reviewed.append({**row, "decision": decision, "review_note": note})
    found_accepts = {(row["chinese"], row["english"]) for row in reviewed if row["decision"] == "accept"}
    missing = set(ACCEPTED) - found_accepts
    if missing:
        raise SystemExit(f"Curated NAER accounting decisions absent from candidates: {sorted(missing)}")
    if len(found_accepts) != len(ACCEPTED):
        raise SystemExit("Unexpected accepted NAER accounting pair")
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
            raise SystemExit(f"Accepted NAER accounting mapping is already mapped or unreachable: {chinese} -> {english}")
        if inputs["extras"].get(chinese, 0) + per_key[chinese] >= 8:
            raise SystemExit(f"Accepted NAER accounting mapping exceeds per-key expansion limit: {chinese} -> {english}")
        per_key[chinese] += 1
        expansion_rows.append({"chinese": chinese, "english": english, "pos": "n.", "source": SOURCE})
    expansion_rows.sort(key=lambda row: (row["chinese"], row["english"]))
    exact_by_word: dict[str, list[dict[str, str]]] = {}
    for row in prefilter:
        exact_by_word.setdefault(row["english"], []).append(row)
    source_headwords = set(exact_by_word)
    reviewed_tag_headwords = set(TAG_ACCEPTED) | set(TAG_REJECTED) | set(TAG_DEFERRED)
    if (set(TAG_ACCEPTED) & set(TAG_REJECTED)) or (set(TAG_ACCEPTED) & set(TAG_DEFERRED)) or (set(TAG_REJECTED) & set(TAG_DEFERRED)):
        raise SystemExit("Accounting tag review decisions overlap")
    unreviewed_tag_headwords = source_headwords - reviewed_tag_headwords
    unexpected_tag_reviews = reviewed_tag_headwords - source_headwords
    if unreviewed_tag_headwords or unexpected_tag_reviews:
        raise SystemExit(
            f"Accounting tag review coverage mismatch: unreviewed={sorted(unreviewed_tag_headwords)}, "
            f"unexpected={sorted(unexpected_tag_reviews)}"
        )
    tag_decisions = {word: note for word, note in TAG_ACCEPTED.items() if word in exact_by_word}
    for row in accepted:
        if row["english"] not in tag_decisions:
            raise SystemExit(f"Accepted accounting mapping has no reviewed accounting tag: {row['english']}")
    tag_deferred_without_exact = set(TAG_ACCEPTED) - source_headwords
    tag_words = sorted(tag_decisions)
    tag_rows = [{"english": word, "mask": str(BUSINESS_BIT), "source": SOURCE} for word in tag_words]
    tag_review_rows = []
    for word, note in sorted(tag_decisions.items()):
        matching = exact_by_word[word]
        tag_review_rows.append({
            "english": word,
            "source_records": ",".join(sorted({n for row in matching for n in row["source_records"].split(",")}, key=int)),
            "source_pairs": " | ".join(f"{row['chinese']} -> {word}" for row in matching),
            "already_business_tag": str(word in inputs["existing_business_words"]).lower(),
            "decision": "accept",
            "review_note": note,
        })
    for decision, source in (("reject", TAG_REJECTED), ("defer", TAG_DEFERRED)):
        for word, note in sorted(source.items()):
            matching = exact_by_word[word]
            tag_review_rows.append({
                "english": word,
                "source_records": ",".join(sorted({n for row in matching for n in row["source_records"].split(",")}, key=int)),
                "source_pairs": " | ".join(f"{row['chinese']} -> {word}" for row in matching),
                "already_business_tag": str(word in inputs["existing_business_words"]).lower(),
                "decision": decision,
                "review_note": note,
            })
    for word in sorted(tag_deferred_without_exact):
        tag_review_rows.append({
            "english": word,
            "source_records": "",
            "source_pairs": "",
            "already_business_tag": str(word in inputs["existing_business_words"]).lower(),
            "decision": "defer",
            "review_note": "No exact local ECDICT gloss, pinyin key, and IPA combination was found for this source headword; no business tag is added.",
        })
    tag_review_rows.sort(key=lambda row: row["english"])
    prefilter_bytes = write_tsv(PREFILTER, PREFILTER_FIELDS, prefilter)
    candidate_bytes = write_tsv(CANDIDATES, PREFILTER_FIELDS, candidates)
    reviewed_bytes = write_tsv(REVIEWED, REVIEW_FIELDS, reviewed)
    tag_review_bytes = write_tsv(TAG_REVIEWED, TAG_FIELDS, tag_review_rows)
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
        "batch": "32-naer-accounting-terms",
        "source": {
            "title": "National Academy for Educational Research - Accounting Academic Terms",
            "provider": "National Academy for Educational Research",
            "dataset_id": "15404",
            "dataset_url": "https://data.gov.tw/dataset/15404",
            "resource_url": "https://opendata.naer.edu.tw/學術名詞/國家教育研究院-會計學學術名詞.csv",
            "license": "Open Government Data License v1.0",
            "license_url": "https://data.gov.tw/license",
            "portal_updated_at": "2026-08-12 14:00",
            "snapshot_sha256": SOURCE_SHA256,
            "snapshot_bytes": SOURCE_CSV.stat().st_size,
            "records": source_record_count,
        },
        "filters": {
            "source_scope": "One-word English glossary terms with local IPA, exact ECDICT noun gloss, exact pinyin key, and per-key expansion capacity.",
            "candidate_scope": "Previously unmapped pairs receive explicit accept/reject/defer decisions; only concise accounting-relevant senses ship. Existing exact source terms can receive a business-category membership after source and local dictionary validation.",
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
            "accounting_tag_source_memberships": len(tag_rows),
            "reviewed_tag_headwords": len(source_headwords),
            "rejected_tag_headwords": len(TAG_REJECTED),
            "deferred_tag_headwords": len(TAG_DEFERRED) + len(tag_deferred_without_exact),
            "deferred_tag_headwords_without_exact_local_pair": len(tag_deferred_without_exact),
        },
        "accepted_pairs": [f"{row['chinese']} -> {row['english']} (n.)" for row in accepted],
        "source_hashes": source_hashes,
        "base_lexicon_hashes": inputs["hashes"],
        "outputs": {
            PREFILTER.relative_to(DATA).as_posix(): sha(prefilter_bytes),
            CANDIDATES.relative_to(DATA).as_posix(): sha(candidate_bytes),
            REVIEWED.relative_to(DATA).as_posix(): sha(reviewed_bytes),
            TAG_REVIEWED.relative_to(DATA).as_posix(): sha(tag_review_bytes),
            EXPANSION.relative_to(DATA).as_posix(): sha(expansion_bytes),
            TAGS.relative_to(DATA).as_posix(): sha(tags_bytes),
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
