"""Build a reviewed finance vocabulary tranche from CFPB's public glossary."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
SOURCE_FILE = DATA / "sources/cfpb/cfpb-financial-glossary-2024.md"
CURATION = DATA / "batches/18-cfpb-finance-reviewed.tsv"
CANDIDATES = DATA / "batches/18-cfpb-finance-candidates.tsv"
EXPANSION = DATA / "cfpb-finance-expansion.tsv"
TAGS = DATA / "cfpb-finance-tags.tsv"
MANIFEST = DATA / "cfpb-finance-manifest.json"
SOURCE = "CFPB Chinese-English financial glossary 2024"
UPSTREAM = "https://files.consumerfinance.gov/f/documents/cfpb_adult-fin-ed_chinese-style-guide-glossary.pdf"
SOURCE_SHA256 = "e319ee28ae2a0a3a36995ec437386f9813ed2a67b6367def90447a60a3c7bbda"
BUSINESS_BIT = 1 << 7
POS_MARKERS = {"n.": "n.", "v.": "v.", "adj.": "adj.", "adv.": "adv."}
POS_PATTERN = re.compile(r"\((n\.|v\.|adj\.|adv\.)\)", re.I)
ENGLISH_TERM = re.compile(r"[a-z][a-z0-9]*(?:[-'][a-z0-9]+)*(?: [a-z][a-z0-9]*(?:[-'][a-z0-9]+)*)*\Z")
HAN = re.compile(r"[\u3400-\u9fff]+")
FIELDS = (
    "chinese", "english", "pos", "source_english", "source_chinese", "source_pos",
    "source_line", "pinyin", "pinyin_frequency", "has_uk_ipa", "has_us_ipa",
    "already_mapped", "already_headword", "extra_count", "ecdict_exact_pos",
    "ecdict_rows", "decision", "review_note",
)
ACCEPTED = {
    ("减轻", "abatement", "n."), ("废除", "abrogate", "v."),
    ("加速", "acceleration", "n."),
    ("确认", "acknowledgement", "n."), ("评估", "assessment", "n."),
    ("转让", "assignment", "n."), ("作证", "attest", "v."),
    ("经纪人", "broker", "n."), ("费用", "charge", "n."),
    ("动产", "chattel", "n."), ("强迫", "coerce", "v."),
    ("补偿", "compensation", "n."), ("让步", "concession", "n."),
    ("转换", "conversion", "n."), ("转让", "convey", "v."),
    ("契约", "covenant", "n."), ("判决", "decree", "n."),
    ("扣除", "deduction", "n."), ("契约", "deed", "n."),
    ("违约", "default", "n."), ("延期", "deferment", "n."),
    ("延期", "deferral", "n."), ("背书", "endorsement", "n."),
    ("登记", "enrollment", "n."), ("权利", "entitlement", "n."),
    ("费用", "fee", "n."), ("受托人", "fiduciary", "n."),
    ("融资", "financing", "n."), ("基金", "funds", "n."),
    ("租赁", "leasehold", "n."), ("垄断", "monopoly", "n."),
    ("通知", "notice", "n."), ("占用", "occupancy", "n."),
    ("透支", "overdraft", "n."), ("付款", "payment", "n."),
    ("处罚", "penalty", "n."), ("免除", "release", "v."),
    ("解除", "release", "v."), ("汇款", "remittance", "n."),
    ("取消", "rescind", "v."), ("报复", "retaliation", "n."),
    ("撤回", "revoke", "v."), ("扣押", "seize", "v."),
    ("没收", "seizure", "n."), ("结算", "settlement", "n."),
    ("法规", "statute", "n."), ("约定", "stipulation", "n."),
    ("转租", "sublease", "v."), ("津贴", "subsidy", "n."),
    ("传票", "summons", "n."), ("条款", "terms", "n."),
    ("估价", "valuation", "n."), ("工资", "wages", "n."),
    ("担保", "warranty", "n."),
    ("分配", "assignment", "n."), ("捐赠", "donation", "n."),
    ("丧失", "forfeiture", "n."), ("受雇", "hire", "v."),
    ("识别", "identification", "n."), ("调查", "inquiry", "n."),
    ("占有", "occupancy", "n."), ("条例", "ordinances", "n."),
    ("所有人", "owner", "n."), ("财产", "possession", "n."),
    ("暂停", "suspension", "n."), ("公用事业", "utilities", "n."),
    ("违背", "violation", "n."),
}
ACCEPT_NOTES = {
    ("分配", "assignment", "n."): "The CFPB entry lists 分配 for the noun assignment; the exact ECDICT gloss agrees. In finance/legal usage this covers assignment or allocation of rights and funds.",
    ("捐赠", "donation", "n."): "The CFPB and ECDICT both give 捐赠 as the noun donation; a direct monetary-giving term in consumer-finance materials.",
    ("丧失", "forfeiture", "n."): "The CFPB entry lists 丧失 alongside property confiscation and loss of rights; ECDICT confirms the exact noun gloss, so this is retained in its legal/financial context.",
    ("受雇", "hire", "v."): "The CFPB entry lists 受雇 for hire, and ECDICT confirms the verb; this is the employment-side sense used in consumer-finance material.",
    ("识别", "identification", "n."): "The CFPB entry includes 识别 and 身份识别; ECDICT confirms the exact noun gloss, which is relevant to identity verification.",
    ("调查", "inquiry", "n."): "The CFPB entry lists 调查 among the noun senses of inquiry; the exact ECDICT gloss agrees in an investigation/credit-inquiry context.",
    ("占有", "occupancy", "n."): "The CFPB entry lists 占有 for occupancy; ECDICT confirms the noun gloss in a real-estate/property context.",
    ("条例", "ordinances", "n."): "The CFPB glossary directly maps 条例 to ordinances; ECDICT confirms the plural noun gloss in a regulatory/legal context.",
    ("所有人", "owner", "n."): "The CFPB entry lists 所有人, 物主, and 业主 for owner; ECDICT confirms the exact noun gloss for property ownership.",
    ("财产", "possession", "n."): "The CFPB entry lists 财产 among noun senses of possession; ECDICT confirms the exact gloss in a property/legal context.",
    ("暂停", "suspension", "n."): "The CFPB entry directly maps 暂停 to suspension; ECDICT confirms the noun gloss, applicable to suspension of a payment, benefit, or service.",
    ("公用事业", "utilities", "n."): "The CFPB entry directly maps 公用事业 to utilities and ECDICT confirms the noun; this is a consumer household-finance category.",
    ("违背", "violation", "n."): "The CFPB entry lists 违背 among noun senses of violation; ECDICT confirms the exact legal gloss in consumer-financial regulation.",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def runtime_inputs():
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.path.insert(0, str(ROOT / "build/vocabulary-research/skywind3000__ECDICT"))
    sys.path.insert(0, str(ROOT / "build/vocab-tools"))
    from build_professional_vocabulary import inputs, verify_inputs

    input_hashes = verify_inputs()
    return (*inputs(), input_hashes)


def cjk_options(text: str, converter) -> set[str]:
    """Return direct glossary chunks and their whitespace-joined forms."""
    options: set[str] = set()
    for segment in re.split(r"[，,、;；/／|]", text):
        runs = [converter.convert(part) for part in HAN.findall(segment)]
        for run in runs:
            if run:
                options.add(run)
        # CFPB PDF extraction sometimes separates a single Chinese term with spaces.
        # Check joined spans against ECDICT and the pinyin lexicon before accepting.
        for start in range(len(runs)):
            joined = ""
            for end in range(start, len(runs)):
                joined += runs[end]
                if len(joined) <= 12:
                    options.add(joined)
    return options


def source_rows() -> list[dict[str, str]]:
    raw = SOURCE_FILE.read_bytes()
    if sha(raw) != SOURCE_SHA256:
        raise SystemExit("Pinned CFPB glossary snapshot SHA-256 mismatch")
    text = raw.decode("utf-8")
    try:
        from opencc import OpenCC
    except ImportError as error:
        raise SystemExit("Pinned OpenCC tooling is required") from error
    converter = OpenCC("t2s")
    active = False
    rows = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.strip() == "# Glossary":
            active = True
            continue
        if not active:
            continue
        fields = re.split(r"\s{2,}", line.strip(), maxsplit=1)
        if len(fields) != 2:
            continue
        english, chinese_text = fields[0].strip().casefold(), fields[1].strip()
        if english in {"english", "numeric"} or not ENGLISH_TERM.fullmatch(english):
            continue
        pos_markers = {POS_MARKERS[m.casefold()] for m in POS_PATTERN.findall(chinese_text)}
        cleaned = POS_PATTERN.sub(" ", chinese_text)
        cleaned = re.sub(r"\([^)]*depending on context[^)]*\)", " ", cleaned, flags=re.I)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        for chinese in cjk_options(cleaned, converter):
            if chinese:
                rows.append({
                    "english": english,
                    "source_english": fields[0].strip(),
                    "source_chinese": cleaned,
                    "source_pos": ",".join(sorted(pos_markers)),
                    "source_line": str(line_number),
                    "chinese": chinese,
                })
    return rows


def discover() -> list[dict[str, str]]:
    baseline, pairs, existing_words, extras, pinyin, _ipa, ecdict, ecdict_rows, hashes = runtime_inputs()
    del baseline
    uk = {line.split("\t", 1)[0].strip().casefold() for line in (ROOT / "pronunciation/source/en_UK.txt").read_text(encoding="utf-8").splitlines() if "\t" in line}
    us = {line.split("\t", 1)[0].strip().casefold() for line in (ROOT / "pronunciation/source/en_US.txt").read_text(encoding="utf-8").splitlines() if "\t" in line}
    pair_set = {(zh, en.casefold()) for zh, en in pairs}
    all_words = {word.casefold() for word in existing_words}
    collected: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in source_rows():
        chinese, english = row["chinese"], row["english"]
        if chinese not in pinyin or english not in uk | us:
            continue
        exact = ecdict.get(english, set())
        source_pos = set(row["source_pos"].split(",")) - {""}
        exact_pos = sorted(pos for gloss, pos in exact if gloss == chinese and (not source_pos or pos in source_pos))
        for pos in exact_pos:
            key = (chinese, english, pos)
            previous = collected.get(key)
            if previous is None:
                collected[key] = {
                    **row,
                    "pos": pos,
                    "pinyin": pinyin[chinese][0],
                    "pinyin_frequency": str(pinyin[chinese][1]),
                    "has_uk_ipa": str(english in uk).lower(),
                    "has_us_ipa": str(english in us).lower(),
                    "already_mapped": str((chinese, english) in pair_set).lower(),
                    "already_headword": str(english in all_words).lower(),
                    "extra_count": str(extras[chinese]),
                    "ecdict_exact_pos": pos,
                    "ecdict_rows": ",".join(map(str, sorted(ecdict_rows.get((english, chinese, pos), set())))),
                }
            else:
                # Keep all source witnesses in the evidence while making generation deterministic.
                source_terms = set(previous["source_english"].split(" | "))
                source_terms.add(row["source_english"])
                previous["source_english"] = " | ".join(sorted(source_terms, key=str.casefold))
                source_lines = set(previous["source_line"].split(","))
                source_lines.add(row["source_line"])
                previous["source_line"] = ",".join(sorted(source_lines, key=int))
    return sorted(collected.values(), key=lambda row: (row["english"], row["chinese"], row["pos"]))


def bootstrap(rows: list[dict[str, str]]) -> None:
    if CURATION.exists():
        raise SystemExit(f"Refusing to overwrite review file: {CURATION}")
    decisions = []
    for row in rows:
        key = (row["chinese"], row["english"], row["pos"])
        if key in ACCEPTED:
            decision, note = "accept", ACCEPT_NOTES.get(key, "The CFPB financial glossary gives this Chinese equivalent in a consumer-finance or legal context; the exact ECDICT gloss and part of speech agree, the pinyin key is present, and local IPA is available.")
        elif row["already_mapped"] == "true":
            decision, note = "reject", "This exact mapping already exists; preserve the current translation and Chinese candidate order."
        elif int(row["extra_count"]) >= 8:
            decision, note = "reject", "The Chinese key has reached the reviewed expansion limit."
        else:
            decision, note = "defer", "Not selected in this small tranche. Source and ECDICT support a candidate pair, but this exact sense was not individually adjudicated for a finance-specific mapping; defer rather than add a possibly overbroad gloss."
        decisions.append({"chinese": row["chinese"], "english": row["english"], "pos": row["pos"], "decision": decision, "review_note": note})
    with CURATION.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("chinese", "english", "pos", "decision", "review_note"), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(decisions)


def decisions_for(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    expected = {(row["chinese"], row["english"], row["pos"]) for row in rows}
    decisions = {}
    with CURATION.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if tuple(reader.fieldnames or ()) != ("chinese", "english", "pos", "decision", "review_note"):
            raise SystemExit("Unexpected CFPB review columns")
        for row in reader:
            key = (row["chinese"], row["english"], row["pos"])
            if key in decisions or key not in expected or row["decision"] not in {"accept", "reject", "defer"} or not row["review_note"].strip():
                raise SystemExit(f"Invalid or stale CFPB review decision: {key}")
            decisions[key] = row
    if set(decisions) != expected:
        raise SystemExit(f"CFPB curation incomplete: {len(expected - set(decisions))} decisions missing")
    return [decisions[(r["chinese"], r["english"], r["pos"])] for r in rows]


def build(rows: list[dict[str, str]] | None = None) -> dict[Path, bytes]:
    rows = rows if rows is not None else discover()
    decisions = decisions_for(rows)
    accepted = [r for r, d in zip(rows, decisions) if d["decision"] == "accept"]
    if {(r["chinese"], r["english"], r["pos"]) for r in accepted} != ACCEPTED:
        raise SystemExit("The reviewed CFPB tranche changed; update the explicit accepted mapping set")
    _, pairs, existing_words, extras, pinyin, _ipa, _ecdict, _ecdict_rows, hashes = runtime_inputs()
    pair_set = {(zh, en.casefold()) for zh, en in pairs}
    per_key: dict[str, int] = defaultdict(int)
    expansion_rows = []
    for row in accepted:
        zh, en = row["chinese"], row["english"]
        if (zh, en) in pair_set or zh not in pinyin or int(row["extra_count"]) + per_key[zh] >= 8:
            raise SystemExit(f"Accepted CFPB mapping violates duplicate, pinyin, or expansion limit: {zh} -> {en}")
        per_key[zh] += 1
        expansion_rows.append(f"{zh}\t{en}\t{row['pos']}\t{SOURCE}\n")
    expansion = "".join(sorted(expansion_rows, key=str.casefold)).encode("utf-8")

    accepted_heads = {r["english"] for r in accepted}
    known_heads = {word.casefold() for word in existing_words}
    tag_words = sorted({r["english"] for r in rows if r["english"] in known_heads | accepted_heads})
    tags = "".join(f"{word}\t{BUSINESS_BIT}\tCFPB 2024 public-domain glossary\n" for word in tag_words).encode("utf-8")
    existing_business = set()
    for filename in ("professional-domain-tags.tsv", "fibo-business-tags.tsv", "better-quant-business-tags.tsv"):
        path = DATA / filename
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            fields = line.split("\t")
            if len(fields) >= 2 and int(fields[1]) & BUSINESS_BIT:
                existing_business.add(fields[0].casefold())
    candidate_pairs = {(r["chinese"], r["english"]) for r in rows}
    mapped_pairs = {
        (r["chinese"], r["english"])
        for r in rows if r["already_mapped"] == "true"
    } | {(r["chinese"], r["english"]) for r in accepted}

    from io import StringIO
    evidence_out = StringIO(newline="")
    writer = csv.DictWriter(evidence_out, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for row, decision in zip(rows, decisions):
        writer.writerow({**row, "decision": decision["decision"], "review_note": decision["review_note"]})
    evidence = evidence_out.getvalue().encode("utf-8")
    manifest = {
        "batch": "18-cfpb-consumer-finance",
        "source_url": UPSTREAM,
        "source_date": "2024-03",
        "source_snapshot_sha256": SOURCE_SHA256,
        "source_snapshot_bytes": SOURCE_FILE.stat().st_size,
        "source_terms_parsed": len({(r["source_english"], r["source_line"]) for r in source_rows()}),
        "candidate_mappings_with_pinyin_ipa_exact_ecdict": len(rows),
        "accepted_new_mappings": len(accepted),
        "deferred_candidate_mappings": sum(d["decision"] == "defer" for d in decisions),
        "rejected_duplicate_or_capacity_candidates": sum(d["decision"] == "reject" for d in decisions),
        "rejected_existing_mappings": sum(r["already_mapped"] == "true" for r in rows),
        "rejected_capacity_candidates": sum(r["already_mapped"] == "false" and int(r["extra_count"]) >= 8 for r in rows),
        "accepted_new_english_headwords": len({r["english"] for r in accepted if r["already_headword"] == "false"}),
        "accepted_mapping_rows": [f"{r['chinese']} -> {r['english']} ({r['pos']})" for r in accepted],
        "candidate_unique_chinese_english_pairs": len(candidate_pairs),
        "mapped_unique_candidate_pairs": len(mapped_pairs),
        "mapped_candidate_pair_coverage": round(len(mapped_pairs) / len(candidate_pairs), 6) if candidate_pairs else 0.0,
        "cfpb_finance_tag_words": len(tag_words),
        "new_business_tag_memberships": len(set(tag_words) - existing_business),
        "tag_semantics": "Membership in the CFPB's public consumer-finance glossary; this source tag supplements, rather than certifies, the broader business category.",
        "runtime_inputs_sha256": hashes,
        "expansion_sha256": sha(expansion),
        "tag_file_sha256": sha(tags),
        "evidence_sha256": sha(evidence),
        "curation_sha256": sha(CURATION.read_bytes()),
        "runtime_note": "Only reviewed exact Chinese-English additions and compact word membership rows are compiled into the lookup index; the 81-page source and audit rows stay outside the keystroke path.",
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
    rows = discover()
    if args.discover:
        print(json.dumps({"candidate_count": len(rows), "candidates": rows}, ensure_ascii=False, indent=2))
    elif args.bootstrap_curation:
        bootstrap(rows)
        print(f"Wrote {len(rows)} explicit review decisions to {CURATION.relative_to(ROOT)}")
    else:
        for path, content in build(rows).items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            print(f"{path.relative_to(ROOT)}: {len(content)} bytes")


if __name__ == "__main__":
    main()
