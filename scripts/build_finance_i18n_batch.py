"""Build a small, reviewed finance tranche from the MIT-licensed finance_i18n list.

The upstream list is broad and gives no earlier data provenance, so it is only
used for candidate discovery. Runtime additions require an exact ECDICT gloss
and POS, a real local pinyin key, local IPA, spare capacity, and an explicit
curation decision.
"""
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
SOURCE_FILE = DATA / "sources/finance_i18n/README.md"
LICENSE_FILE = DATA / "sources/finance_i18n/LICENSE"
CURATION = DATA / "batches/19-finance-i18n-reviewed.tsv"
CANDIDATES = DATA / "batches/19-finance-i18n-candidates.tsv"
EXPANSION = DATA / "finance-i18n-expansion.tsv"
TAGS = DATA / "finance-i18n-tags.tsv"
MANIFEST = DATA / "finance-i18n-manifest.json"
UPSTREAM = "https://github.com/hotvulcan/finance_i18n"
COMMIT = "98a75886853e586c55896878bfab88e1161f50df"
SOURCE_SHA256 = "60e07fb4bb98c217031c09f97fcc66472b0cfc0c102de639769c0fb7904e2e71"
LICENSE_SHA256 = "6f53e33c175f680f00700b220cd81ecd8f9af4e872c4bd737262d021ef6fd678"
BUSINESS_BIT = 1 << 7
PREEXISTING_EXPANSIONS = (
    "batches/02-additions.tsv",
    "better-quant-expansion.tsv",
    "cccedict-expansion-2.tsv",
    "cccedict-expansion-3.tsv",
    "cccedict-expansion-4.tsv",
    "cccedict-expansion.tsv",
    "cfpb-finance-expansion.tsv",
    "cjk-compsci-expansion.tsv",
    "english-expansion.tsv",
    "exam-target-batch-11-cc-by-sa-expansion.tsv",
    "exam-target-batch-11-cow-expansion.tsv",
    "exam-target-batch-11-dual-expansion.tsv",
    "exam-target-batch-11-ecdict-expansion.tsv",
    "exam-target-batch-11-koreader-cow-expansion.tsv",
    "exam-target-batch-11-kylebing-expansion.tsv",
    "exam-target-batch-12-ecdict-expansion.tsv",
    "exam-target-ecdict-expansion.tsv",
    "exam-target-kylebing-expansion.tsv",
    "openetymology-exam-expansion.tsv",
    "professional-expansion.tsv",
    "wiktionary-expansion-2.tsv",
    "wiktionary-expansion.tsv",
)
HAN = re.compile(r"[\u3400-\u9fff]+")
WORD = re.compile(r"[a-z]+(?:[-'][a-z]+)*\Z")
FIELDS = (
    "chinese", "english", "pos", "source_line", "source_row", "pinyin",
    "pinyin_frequency", "has_uk_ipa", "has_us_ipa", "already_mapped",
    "already_headword", "existing_extra_count", "ecdict_rows", "decision",
    "review_note",
)

# Reviewed one-pair decisions. These cover finance/accounting, tax, trade,
# securities, property, and associated contract terms; generic candidates stay deferred.
ACCEPTED = {
    ("累积", "accumulation", "n."),
    ("分摊", "apportionment", "n."),
    ("估价", "appraisal", "n."),
    ("遗赠", "bequest", "n."),
    ("特许", "concession", "n."),
    ("关税", "customs", "n."),
    ("买卖", "deal", "n."),
    ("没收", "confiscation", "n."),
    ("废止", "defeasance", "n."),
    ("贬值", "devaluation", "n."),
    ("支付", "disbursement", "n."),
    ("倾销", "dumping", "n."),
    ("盗用", "embezzlement", "n."),
    ("国库", "exchequer", "n."),
    ("征用", "expropriation", "n."),
    ("免税", "exemption", "n."),
    ("发行", "float", "v."),
    ("底价", "floor", "n."),
    ("供过于求", "glut", "n."),
    ("赔偿", "indemnity", "n."),
    ("契约", "indenture", "n."),
    ("投资", "investment", "n."),
    ("地产", "land", "n."),
    ("行情", "market", "n."),
    ("债务", "obligation", "n."),
    ("报价", "offer", "n."),
    ("平价", "parity", "n."),
    ("抵押", "pledge", "n."),
    ("联营", "pool", "n."),
    ("赎回", "redemption", "n."),
    ("救济", "relief", "n."),
    ("报酬", "remuneration", "n."),
    ("偿还", "restitution", "n."),
    ("动产", "personalty", "n."),
    ("投机", "speculation", "n."),
    ("附加税", "surcharge", "n."),
    ("担保", "surety", "n."),
    ("进款", "takings", "n."),
    ("过户", "transfer", "n."),
    ("提款", "withdrawal", "n."),
    ("价值", "worth", "n."),
    ("公用事业", "utility", "n."),
    ("不动产", "realty", "n."),
    ("走私", "smuggling", "n."),
    ("硬币", "specie", "n."),
    ("买主", "vendee", "n."),
    ("卖主", "vendor", "n."),
}

ACCEPT_NOTES = {
    ("累积", "accumulation", "n."): "The source pairs accumulation with 累积; ECDICT confirms the exact noun gloss. Retained as a financial/accounting accumulation term.",
    ("分摊", "apportionment", "n."): "The source pairs apportionment with 分摊; ECDICT confirms the exact noun gloss. This is a cost and allocation term.",
    ("估价", "appraisal", "n."): "The source pairs appraisal with 估价; ECDICT confirms the exact noun gloss. Asset and property appraisal is relevant to finance.",
    ("遗赠", "bequest", "n."): "The source pairs bequest with 遗赠; ECDICT confirms the exact noun gloss. This is an estate and property-transfer term.",
    ("特许", "concession", "n."): "The source pairs concession with 特许; ECDICT confirms the exact noun gloss used for commercial concessions.",
    ("关税", "customs", "n."): "The source pairs customs with 关税; ECDICT confirms the exact noun gloss in a trade/tax context.",
    ("买卖", "deal", "n."): "The source pairs deal with 买卖; ECDICT confirms the exact noun gloss. This is a commercial transaction sense.",
    ("没收", "confiscation", "n."): "The source pairs confiscation with 没收; ECDICT confirms the exact noun gloss in a legal/financial enforcement sense.",
    ("废止", "defeasance", "n."): "The source pairs defeasance with 废止; ECDICT confirms the exact noun gloss. Retained as a specialized contract/legal term.",
    ("贬值", "devaluation", "n."): "The source pairs devaluation with 贬值; ECDICT confirms the exact noun gloss used in currency and asset valuation.",
    ("支付", "disbursement", "n."): "The source pairs disbursement with 支付; ECDICT confirms the exact noun gloss. This is a finance and accounting payment term.",
    ("倾销", "dumping", "n."): "The source pairs dumping with 倾销; ECDICT confirms the exact noun gloss in international trade.",
    ("盗用", "embezzlement", "n."): "The source pairs embezzlement with 盗用; ECDICT confirms the exact noun gloss for financial misconduct.",
    ("国库", "exchequer", "n."): "The source pairs exchequer with 国库; ECDICT confirms the exact noun gloss. Marked as a government-finance term.",
    ("征用", "expropriation", "n."): "The source pairs expropriation with 征用; ECDICT confirms the exact noun gloss for a property/legal context.",
    ("免税", "exemption", "n."): "The source pairs exemption with 免税; ECDICT confirms the exact noun gloss in a tax context.",
    ("发行", "float", "v."): "The source pairs float with 发行; ECDICT confirms the exact verb gloss. Retained for issuing securities or shares.",
    ("底价", "floor", "n."): "The source pairs floor with 底价; ECDICT confirms the exact noun gloss used for a minimum price/price floor.",
    ("供过于求", "glut", "n."): "The source pairs glut with 供过于求; ECDICT confirms the exact noun gloss. This is a market-supply term.",
    ("赔偿", "indemnity", "n."): "The source pairs indemnity with 赔偿; ECDICT confirms the exact noun gloss used in insurance and contracts.",
    ("契约", "indenture", "n."): "The source pairs indenture with 契约; ECDICT confirms the exact noun gloss. This is a contract/securities term.",
    ("投资", "investment", "n."): "The source pairs investment with 投资; ECDICT confirms the exact noun gloss.",
    ("地产", "land", "n."): "The source pairs land with 地产; ECDICT confirms the exact noun gloss in a property context.",
    ("行情", "market", "n."): "The source pairs market with 行情; ECDICT confirms the exact noun gloss used for market conditions/quotes.",
    ("债务", "obligation", "n."): "The source pairs obligation with 债务; ECDICT confirms the exact noun gloss in a debt/contract context.",
    ("报价", "offer", "n."): "The source pairs offer with 报价; ECDICT confirms the exact noun gloss used in an offer/pricing context.",
    ("平价", "parity", "n."): "The source pairs parity with 平价; ECDICT confirms the exact noun gloss used in exchange-rate and price parity.",
    ("抵押", "pledge", "n."): "The source pairs pledge with 抵押; ECDICT confirms the exact noun gloss in collateral/secured finance.",
    ("联营", "pool", "n."): "The source pairs pool with 联营; ECDICT confirms the exact noun gloss in a business/investment grouping sense.",
    ("赎回", "redemption", "n."): "The source pairs redemption with 赎回; ECDICT confirms the exact noun gloss for securities and financial instruments.",
    ("救济", "relief", "n."): "The source pairs relief with 救济; ECDICT confirms the exact noun gloss used in legal/financial remedy contexts.",
    ("报酬", "remuneration", "n."): "The source pairs remuneration with 报酬; ECDICT confirms the exact noun gloss used in compensation and employment finance.",
    ("偿还", "restitution", "n."): "The source pairs restitution with 偿还; ECDICT confirms the exact noun gloss in repayment/legal contexts.",
    ("动产", "personalty", "n."): "The source pairs personalty with 动产; ECDICT confirms the exact noun gloss. Retained as a specialized property-law term.",
    ("投机", "speculation", "n."): "The source pairs speculation with 投机; ECDICT confirms the exact noun gloss used in financial markets.",
    ("附加税", "surcharge", "n."): "The source pairs surcharge with 附加税; ECDICT confirms the exact noun gloss in taxation.",
    ("担保", "surety", "n."): "The source pairs surety with 担保; ECDICT confirms the exact noun gloss in credit and contract contexts.",
    ("进款", "takings", "n."): "The source pairs takings with 进款; ECDICT confirms the exact noun gloss for money received/revenue.",
    ("过户", "transfer", "n."): "The source pairs transfer with 过户; ECDICT confirms the exact noun gloss used for property/title transfer.",
    ("提款", "withdrawal", "n."): "The source pairs withdrawal with 提款; ECDICT confirms the exact noun gloss in banking.",
    ("价值", "worth", "n."): "The source pairs worth with 价值; ECDICT confirms the exact noun gloss used in valuation.",
    ("公用事业", "utility", "n."): "The source pairs utility with 公用事业; ECDICT confirms the exact noun gloss used as a business/sector term.",
    ("不动产", "realty", "n."): "The source pairs realty with 不动产; ECDICT confirms the exact noun gloss in property terminology.",
    ("走私", "smuggling", "n."): "The source pairs smuggling with 走私; ECDICT confirms the exact noun gloss in customs/trade compliance.",
    ("硬币", "specie", "n."): "The source pairs specie with 硬币; ECDICT confirms the exact noun gloss for coin money.",
    ("买主", "vendee", "n."): "The source pairs vendee with 买主; ECDICT confirms the exact noun gloss in sale/contract terminology.",
    ("卖主", "vendor", "n."): "The source pairs vendor with 卖主; ECDICT confirms the exact noun gloss in commercial transactions.",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_inputs():
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_cfpb_finance_batch as cfpb
    from build_professional_vocabulary import BASELINE, load_base

    checked_inputs = cfpb.runtime_inputs()
    input_hashes = checked_inputs[8]
    baseline = load_base(BASELINE)
    base_pairs = {(zh, word.casefold()) for zh, senses in baseline.items() for word, _ in senses}
    base_words = {word.casefold() for _, word in base_pairs}
    pairs = set(base_pairs)
    words = set(base_words)
    extra_by_key: dict[str, set[str]] = {}

    rust_source = (ROOT / "vocabulary/src/expansion/mod.rs").read_text(encoding="utf-8")
    compiled_files = set(re.findall(r'include_str!\("../../data/([^" ]+\.tsv)"\)', rust_source))
    if not set(PREEXISTING_EXPANSIONS).issubset(compiled_files):
        missing = sorted(set(PREEXISTING_EXPANSIONS) - compiled_files)
        raise SystemExit(f"Pinned preexisting expansions are no longer compiled: {missing}")
    # Freeze the baseline at the point this batch was reviewed. In particular,
    # exclude this batch's own output and any later batches so regeneration
    # cannot reclassify accepted rows as preexisting or drift with future work.
    runtime_files = list(PREEXISTING_EXPANSIONS)
    for filename in runtime_files:
        for line in (DATA / filename).read_text(encoding="utf-8").splitlines():
            fields = line.split("\t")
            if len(fields) < 3:
                continue
            zh, word = fields[0], fields[1].casefold()
            pairs.add((zh, word))
            words.add(word)
            if (zh, word) not in base_pairs:
                extra_by_key.setdefault(zh, set()).add(word)

    pinyin: dict[str, tuple[str, int]] = {}
    for line in (ROOT / "build/pinyin-candidates.tsv").read_text(encoding="utf-8").splitlines():
        zh, code, frequency = line.split("\t")
        pinyin[zh] = (code, int(frequency))

    uk = {line.split("\t", 1)[0].strip().casefold() for line in (ROOT / "pronunciation/source/en_UK.txt").read_text(encoding="utf-8").splitlines() if "\t" in line}
    us = {line.split("\t", 1)[0].strip().casefold() for line in (ROOT / "pronunciation/source/en_US.txt").read_text(encoding="utf-8").splitlines() if "\t" in line}
    # Reuse the already hash-checked ECDICT parser and POS normalization.
    ecdict = checked_inputs[6]
    ecdict_rows = checked_inputs[7]
    try:
        from opencc import OpenCC
    except ImportError as error:
        raise SystemExit("Pinned OpenCC tooling is required") from error

    return {
        "pairs": pairs,
        "words": words,
        "extras": {key: len(value) for key, value in extra_by_key.items()},
        "pinyin": pinyin,
        "uk": uk,
        "us": us,
        "ecdict": ecdict,
        "ecdict_rows": ecdict_rows,
        "hashes": input_hashes,
        "converter": OpenCC("t2s"),
        "runtime_files": runtime_files,
    }


def source_rows(converter) -> list[dict[str, str]]:
    raw = SOURCE_FILE.read_bytes()
    if sha(raw) != SOURCE_SHA256:
        raise SystemExit("Pinned finance_i18n README SHA-256 mismatch")
    if sha(LICENSE_FILE.read_bytes()) != LICENSE_SHA256:
        raise SystemExit("Pinned finance_i18n LICENSE SHA-256 mismatch")
    rows = []
    for line_number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
        if not line or line.startswith("#"):
            continue
        match = HAN.search(line)
        if not match:
            continue
        english = line[:match.start()].strip().casefold().replace("’", "'")
        if not WORD.fullmatch(english):
            continue
        chinese_text = converter.convert(line[match.start():].strip())
        for chunk in re.split(r"[，,、;；/／|]", chinese_text):
            for chinese in HAN.findall(chunk):
                if chinese:
                    rows.append({
                        "english": english,
                        "chinese": chinese,
                        "source_line": str(line_number),
                        "source_row": line.strip(),
                    })
    return rows


def discover(inputs=None) -> list[dict[str, str]]:
    inputs = inputs or load_inputs()
    collected: dict[tuple[str, str, str], dict[str, str]] = {}
    for source in source_rows(inputs["converter"]):
        chinese, english = source["chinese"], source["english"]
        if chinese not in inputs["pinyin"] or english not in inputs["uk"] | inputs["us"]:
            continue
        exact = inputs["ecdict"].get(english, set())
        for pos in sorted({pos for gloss, pos in exact if gloss == chinese}):
            key = (chinese, english, pos)
            existing = collected.get(key)
            if existing is None:
                pinyin, frequency = inputs["pinyin"][chinese]
                collected[key] = {
                    "chinese": chinese,
                    "english": english,
                    "pos": pos,
                    "source_line": source["source_line"],
                    "source_row": source["source_row"],
                    "pinyin": pinyin,
                    "pinyin_frequency": str(frequency),
                    "has_uk_ipa": str(english in inputs["uk"]).lower(),
                    "has_us_ipa": str(english in inputs["us"]).lower(),
                    "already_mapped": str((chinese, english) in inputs["pairs"]).lower(),
                    "already_headword": str(english in inputs["words"]).lower(),
                    "existing_extra_count": str(inputs["extras"].get(chinese, 0)),
                    "ecdict_rows": ",".join(map(str, sorted(inputs["ecdict_rows"].get((english, chinese, pos), set())))),
                }
            else:
                source_lines = set(existing["source_line"].split(","))
                source_lines.add(source["source_line"])
                existing["source_line"] = ",".join(sorted(source_lines, key=int))
    return sorted(collected.values(), key=lambda row: (row["english"], row["chinese"], row["pos"]))


def write_curation(rows: list[dict[str, str]]) -> None:
    if CURATION.exists():
        raise SystemExit(f"Refusing to overwrite review file: {CURATION}")
    output = []
    for row in rows:
        key = (row["chinese"], row["english"], row["pos"])
        if key in ACCEPTED:
            decision, note = "accept", ACCEPT_NOTES[key]
        elif row["already_mapped"] == "true":
            decision, note = "reject", "This exact Chinese-English pair already exists in the compiled vocabulary; do not add a duplicate or alter its order."
        elif int(row["existing_extra_count"]) >= 8:
            decision, note = "reject", "The Chinese key has reached the reviewed expansion limit."
        else:
            decision, note = "defer", "Candidate passed exact ECDICT/POS, local pinyin, and IPA checks, but the upstream list has no earlier data provenance and this pair was not selected for the reviewed finance tranche. Keep it out of runtime data."
        output.append({"chinese": row["chinese"], "english": row["english"], "pos": row["pos"], "decision": decision, "review_note": note})
    with CURATION.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("chinese", "english", "pos", "decision", "review_note"), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(output)


def read_decisions(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    expected = {(row["chinese"], row["english"], row["pos"]) for row in rows}
    decisions = {}
    with CURATION.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if tuple(reader.fieldnames or ()) != ("chinese", "english", "pos", "decision", "review_note"):
            raise SystemExit("Unexpected finance_i18n review columns")
        for row in reader:
            key = (row["chinese"], row["english"], row["pos"])
            if key in decisions or key not in expected or row["decision"] not in {"accept", "reject", "defer"} or not row["review_note"].strip():
                raise SystemExit(f"Invalid or stale finance_i18n decision: {key}")
            decisions[key] = row
    if set(decisions) != expected:
        raise SystemExit(f"finance_i18n curation incomplete: {len(expected - set(decisions))} decisions missing")
    accepted = {(row["chinese"], row["english"], row["pos"]) for row in rows if decisions[(row["chinese"], row["english"], row["pos"])]["decision"] == "accept"}
    if accepted != ACCEPTED:
        raise SystemExit(f"finance_i18n accepted set changed: missing={sorted(ACCEPTED - accepted)}, extra={sorted(accepted - ACCEPTED)}")
    return [decisions[(row["chinese"], row["english"], row["pos"])] for row in rows]


def build(rows: list[dict[str, str]], inputs: dict) -> dict[Path, bytes]:
    decisions = read_decisions(rows)
    accepted = [row for row, decision in zip(rows, decisions) if decision["decision"] == "accept"]
    per_key: Counter[str] = Counter()
    expansion_rows = []
    for row in accepted:
        zh, en = row["chinese"], row["english"]
        if (zh, en) in inputs["pairs"] or zh not in inputs["pinyin"]:
            raise SystemExit(f"Accepted finance_i18n mapping violates pair or pinyin checks: {zh} -> {en}")
        if inputs["extras"].get(zh, 0) + per_key[zh] >= 8:
            raise SystemExit(f"Accepted finance_i18n mapping exceeds per-key expansion limit: {zh} -> {en}")
        per_key[zh] += 1
        expansion_rows.append(f"{zh}\t{en}\t{row['pos']}\tfinance_i18n MIT 2018\n")
    expansion = "".join(sorted(expansion_rows, key=str.casefold)).encode("utf-8")
    tag_words = sorted({row["english"] for row in accepted})
    tags = "".join(f"{word}\t{BUSINESS_BIT}\tfinance_i18n MIT 2018\n" for word in tag_words).encode("utf-8")

    existing_business = set()
    for filename in (
        "professional-domain-tags.tsv", "cjk-compsci-tags.tsv", "fibo-business-tags.tsv",
        "better-quant-business-tags.tsv", "cfpb-finance-tags.tsv",
    ):
        for line in (DATA / filename).read_text(encoding="utf-8").splitlines():
            fields = line.split("\t")
            if len(fields) >= 2 and int(fields[1]) & BUSINESS_BIT:
                existing_business.add(fields[0].casefold())

    from io import StringIO
    evidence_out = StringIO(newline="")
    writer = csv.DictWriter(evidence_out, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for row, decision in zip(rows, decisions):
        writer.writerow({**row, "decision": decision["decision"], "review_note": decision["review_note"]})
    evidence = evidence_out.getvalue().encode("utf-8")
    manifest = {
        "batch": "19-finance-i18n",
        "source_url": UPSTREAM,
        "source_commit": COMMIT,
        "source_commit_date": "2021-05-05",
        "source_snapshot_sha256": SOURCE_SHA256,
        "source_snapshot_bytes": SOURCE_FILE.stat().st_size,
        "source_license_sha256": LICENSE_SHA256,
        "source_license": "MIT License (upstream repository claim)",
        "upstream_provenance_note": "The upstream README does not identify an earlier origin for the bilingual list; it is used as a candidate source only. Entries require exact ECDICT Chinese gloss/POS, local pinyin and IPA, and explicit review before runtime inclusion.",
        "source_rows_with_chinese": sum(1 for line in SOURCE_FILE.read_text(encoding="utf-8").splitlines() if line and HAN.search(line)),
        "candidate_pairs_with_exact_ecdict_pinyin_ipa": len(rows),
        "already_mapped_candidate_pairs": sum(row["already_mapped"] == "true" for row in rows),
        "accepted_new_mappings": len(accepted),
        "accepted_new_english_headwords": len({row["english"] for row in accepted if row["already_headword"] == "false"}),
        "new_business_tag_memberships": len(set(tag_words) - existing_business),
        "accepted_mapping_rows": [f"{row['chinese']} -> {row['english']} ({row['pos']})" for row in accepted],
        "runtime_inputs_sha256": inputs["hashes"],
        "runtime_expansion_inputs": list(PREEXISTING_EXPANSIONS),
        "expansion_sha256": sha(expansion),
        "tag_file_sha256": sha(tags),
        "evidence_sha256": sha(evidence),
        "curation_sha256": sha(CURATION.read_bytes()),
        "runtime_note": "Only explicitly reviewed short mappings and business-membership rows enter the compiled lookup; the research snapshot and full audit remain outside the keystroke path.",
    }
    return {
        EXPANSION: expansion,
        TAGS: tags,
        CANDIDATES: evidence,
        MANIFEST: (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--bootstrap-curation", action="store_true")
    args = parser.parse_args()
    inputs = load_inputs()
    rows = discover(inputs)
    if args.discover:
        by_key = {(row["chinese"], row["english"], row["pos"]): row for row in rows}
        print(json.dumps({
            "candidate_count": len(rows),
            "candidate_new_pairs": sum(row["already_mapped"] == "false" for row in rows),
            "candidate_new_headwords": sum(row["already_headword"] == "false" and row["already_mapped"] == "false" for row in rows),
            "accepted_keys_missing_from_candidates": sorted(ACCEPTED - set(by_key)),
            "accepted_keys_already_mapped": sorted(key for key in ACCEPTED if key in by_key and by_key[key]["already_mapped"] == "true"),
            "accepted_keys_at_capacity": sorted(key for key in ACCEPTED if key in by_key and int(by_key[key]["existing_extra_count"]) >= 8),
        }, ensure_ascii=False, indent=2))
    elif args.bootstrap_curation:
        write_curation(rows)
        print(f"Wrote {len(rows)} explicit review decisions to {CURATION.relative_to(ROOT)}")
    else:
        for path, content in build(rows, inputs).items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            print(f"{path.relative_to(ROOT)}: {len(content)} bytes")


if __name__ == "__main__":
    main()
