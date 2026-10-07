"""Build an audited computer-vocabulary tranche from a pinned MIT glossary.

Upstream entries with book-source footnotes and long explanations are excluded.
Only short, one-word entries are candidate evidence; runtime data also requires
an exact local ECDICT gloss/POS, a pinyin key, IPA, and an explicit review.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
SOURCE_DIR = DATA / "sources/computerese-cross-references"
SOURCE_TERMS = SOURCE_DIR / "filtered-terms.tsv"
SOURCE_LICENSE = SOURCE_DIR / "LICENSE"
UPSTREAM_CHECKOUT = ROOT / "build/source-audit/computerese-cross-references"
CURATION = DATA / "batches/20-computerese-reviewed.tsv"
CANDIDATES = DATA / "batches/20-computerese-candidates.tsv"
EVIDENCE = DATA / "batches/20-computerese-evidence.tsv"
EXPANSION = DATA / "computerese-expansion.tsv"
TAGS = DATA / "computerese-tags.tsv"
MANIFEST = DATA / "computerese-manifest.json"
UPSTREAM = "https://github.com/EarsEyesMouth/computerese-cross-references"
COMMIT = "e92ca7dddf6b8122c7c0807f701fa9e237752506"
README_SHA256 = "3f1fb6fb75fe56546380222d5dc7423e2dd36738852bb583e8d99d475a8435fc"
LICENSE_SHA256 = "56a130b3accd55ed0dd1cd9844295f80a1dddf6b2d76a028881324d3d7d96ded"
SOURCE_TERMS_SHA256 = "82d9001532a8a764981b33e4a43aa243841c212147cd70ac40d2cc0047f84030"
SOURCE = "EarsEyesMouth Computerese MIT"
COMPUTER_BIT = 1 << 6
MAX_EXTRA_PER_KEY = 8
WORD = re.compile(r"[a-z]+(?:[-'][a-z]+)*\Z")
HAN = re.compile(r"[\u3400-\u9fff]+")
FOOTNOTE = re.compile(r"<sup>\s*\d+\s*</sup>|\^\{\d+\}", re.I)
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
    "finance-i18n-expansion.tsv",
    "openetymology-exam-expansion.tsv",
    "professional-expansion.tsv",
    "wiktionary-expansion-2.tsv",
    "wiktionary-expansion.tsv",
)
COMPUTER_TAG_FILES = ("professional-domain-tags.tsv", "cjk-compsci-tags.tsv")
SOURCE_FIELDS = ("source_line", "english", "source_meaning")
CANDIDATE_FIELDS = (
    "chinese", "english", "pos", "source_lines", "source_meanings", "pinyin",
    "pinyin_frequency", "ipa_sources", "already_mapped", "already_headword",
    "already_computer_tag", "ecdict_rows",
)
CURATION_FIELDS = CANDIDATE_FIELDS + ("mapping_decision", "tag_decision", "review_note")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bootstrap_source_terms() -> int:
    readme = UPSTREAM_CHECKOUT / "README.md"
    license_path = UPSTREAM_CHECKOUT / "LICENSE"
    if not readme.is_file() or not license_path.is_file():
        raise SystemExit("Pinned upstream checkout is missing README.md or LICENSE")
    revision = subprocess.check_output(
        ["git", "-C", str(UPSTREAM_CHECKOUT), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != COMMIT:
        raise SystemExit(f"Expected upstream commit {COMMIT}, found {revision}")
    if sha(readme.read_bytes()) != README_SHA256:
        raise SystemExit("Pinned computerese README SHA-256 mismatch")
    if sha(license_path.read_bytes()) != LICENSE_SHA256:
        raise SystemExit("Pinned computerese LICENSE SHA-256 mismatch")
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_LICENSE.write_bytes(license_path.read_bytes())

    rows = []
    for line_number, line in enumerate(readme.read_text(encoding="utf-8").splitlines(), 1):
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 2 or cells[0].casefold() == "word" or set(cells[0]) <= set("-:"):
            continue
        english = html.unescape(re.sub(r"<[^>]*>", "", cells[0])).strip()
        meaning = cells[1].strip()
        if FOOTNOTE.search(english) or FOOTNOTE.search(meaning):
            continue
        meaning = html.unescape(re.sub(r"<[^>]*>", "", meaning)).strip()
        if len(meaning) > 24 or not WORD.fullmatch(english.casefold()):
            continue
        if not HAN.search(meaning):
            continue
        rows.append({
            "source_line": str(line_number),
            "english": english.casefold(),
            "source_meaning": meaning,
        })
    with SOURCE_TERMS.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=SOURCE_FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Filtered {len(rows)} short, unfootnoted one-word rows to {SOURCE_TERMS.relative_to(ROOT)}")
    return len(rows)


def load_inputs():
    sys.path[:0] = [
        str(ROOT / "scripts"),
        str(ROOT / "build/vocabulary-research/skywind3000__ECDICT"),
        str(ROOT / "build/vocab-tools"),
    ]
    import build_finance_i18n_batch as finance
    from opencc import OpenCC

    base = finance.load_inputs()
    if sha(SOURCE_LICENSE.read_bytes()) != LICENSE_SHA256:
        raise SystemExit("Pinned computerese MIT license is missing or changed")
    if sha(SOURCE_TERMS.read_bytes()) != SOURCE_TERMS_SHA256:
        raise SystemExit("Filtered computerese source rows are missing or changed")

    rust_source = (ROOT / "vocabulary/src/expansion/mod.rs").read_text(encoding="utf-8")
    compiled = set(re.findall(r'include_str!\("../../data/([^" ]+\.tsv)"\)', rust_source))
    if not set(PREEXISTING_EXPANSIONS).issubset(compiled):
        missing = sorted(set(PREEXISTING_EXPANSIONS) - compiled)
        raise SystemExit(f"Pinned prior expansions are no longer compiled: {missing}")

    existing_computer_tags = set()
    for filename in COMPUTER_TAG_FILES:
        for line in (DATA / filename).read_text(encoding="utf-8").splitlines():
            fields = line.split("\t")
            if len(fields) >= 2 and int(fields[1]) & COMPUTER_BIT:
                existing_computer_tags.add(fields[0].casefold())
    prior_expansion_hashes = {
        filename: sha((DATA / filename).read_bytes())
        for filename in PREEXISTING_EXPANSIONS
    }
    computer_tag_hashes = {
        filename: sha((DATA / filename).read_bytes())
        for filename in COMPUTER_TAG_FILES
    }

    return {
        **base,
        "converter": OpenCC("t2s"),
        "existing_computer_tags": existing_computer_tags,
        "prior_expansions": list(PREEXISTING_EXPANSIONS),
        "prior_expansion_hashes": prior_expansion_hashes,
        "computer_tag_hashes": computer_tag_hashes,
    }


def read_source_terms() -> list[dict[str, str]]:
    with SOURCE_TERMS.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if tuple(reader.fieldnames or ()) != SOURCE_FIELDS:
            raise SystemExit("Unexpected filtered computerese source columns")
        rows = list(reader)
    if len(rows) != 297:
        raise SystemExit(f"Expected 297 filtered source terms; found {len(rows)}")
    return rows


def discover(inputs=None) -> list[dict[str, str]]:
    inputs = inputs or load_inputs()
    collected: dict[tuple[str, str, str], dict[str, set[str] | str]] = {}
    for source_row in read_source_terms():
        english = source_row["english"].strip().casefold()
        if not WORD.fullmatch(english):
            raise SystemExit(f"Invalid filtered English term at source line {source_row['source_line']}")
        meaning = source_row["source_meaning"]
        if FOOTNOTE.search(meaning) or len(meaning) > 24:
            raise SystemExit(f"Excluded source annotation leaked through at line {source_row['source_line']}")
        for chunk in re.split(r"[，,、;；/／|（）()]", meaning):
            for raw_chinese in HAN.findall(chunk):
                chinese = inputs["converter"].convert(raw_chinese)
                if not chinese or len(chinese) > 12 or chinese not in inputs["pinyin"]:
                    continue
                if english not in inputs["uk"] | inputs["us"]:
                    continue
                for pos in sorted({pos for gloss, pos in inputs["ecdict"].get(english, set()) if gloss == chinese}):
                    key = (chinese, english, pos)
                    row = collected.get(key)
                    if row is None:
                        row = {
                            "chinese": chinese,
                            "english": english,
                            "pos": pos,
                            "source_lines": set(),
                            "source_meanings": set(),
                            "pinyin": inputs["pinyin"][chinese][0],
                            "pinyin_frequency": str(inputs["pinyin"][chinese][1]),
                            "ipa_sources": set(),
                            "already_mapped": str((chinese, english) in inputs["pairs"]).lower(),
                            "already_headword": str(english in inputs["words"]).lower(),
                            "already_computer_tag": str(english in inputs["existing_computer_tags"]).lower(),
                            "ecdict_rows": ",".join(map(str, sorted(inputs["ecdict_rows"].get((english, chinese, pos), set())))),
                        }
                        row["ipa_sources"].update(
                            label for label, keys in (("UK", "uk"), ("US", "us"))
                            if english in inputs[keys]
                        )
                        collected[key] = row
                    row["source_lines"].add(source_row["source_line"])
                    row["source_meanings"].add(meaning)

    result = []
    for key in sorted(collected):
        row = collected[key]
        result.append({
            **{field: ",".join(sorted(row[field], key=int if field == "source_lines" else str))
               if isinstance(row[field], set) else str(row[field]) for field in CANDIDATE_FIELDS},
        })
    return result


def write_tsv(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]], *, header: bool = True) -> bytes:
    import io
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t", lineterminator="\n")
    if header:
        writer.writeheader()
    writer.writerows(rows)
    payload = stream.getvalue().encode("utf-8")
    path.write_bytes(payload)
    return payload


def bootstrap_curation(rows: list[dict[str, str]]) -> None:
    if CURATION.exists():
        raise SystemExit(f"Refusing to overwrite review decisions: {CURATION}")
    review = []
    for row in rows:
        existing = row["already_mapped"] == "true"
        review.append({
            **row,
            "mapping_decision": "existing" if existing else "defer",
            "tag_decision": "defer",
            "review_note": "Pending explicit review of computing-domain fit and exact translation.",
        })
    write_tsv(CANDIDATES, CANDIDATE_FIELDS, rows)
    write_tsv(CURATION, CURATION_FIELDS, review)
    print(f"Wrote {len(rows)} candidate rows and explicit review placeholders")


def read_curation(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    expected = {(row["chinese"], row["english"], row["pos"]): row for row in rows}
    if not CURATION.is_file():
        raise SystemExit("Missing explicit computerese review file: " + str(CURATION))
    decisions = {}
    with CURATION.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if tuple(reader.fieldnames or ()) != CURATION_FIELDS:
            raise SystemExit("Unexpected computerese review columns")
        for row in reader:
            key = (row["chinese"], row["english"], row["pos"])
            if key in decisions or key not in expected:
                raise SystemExit(f"Duplicate or stale computerese decision: {key}")
            for field in CANDIDATE_FIELDS:
                if row[field] != expected[key][field]:
                    raise SystemExit(f"Computerese source evidence changed for {key}: {field}")
            allowed_mapping = {"existing"} if row["already_mapped"] == "true" else {"accept", "reject", "defer"}
            if row["mapping_decision"] not in allowed_mapping:
                raise SystemExit(f"Invalid mapping decision for {key}")
            if row["tag_decision"] not in {"accept", "reject", "defer"} or not row["review_note"].strip():
                raise SystemExit(f"Missing explicit tag review or note for {key}")
            decisions[key] = row
    if set(decisions) != set(expected):
        raise SystemExit(f"Incomplete computerese review: {len(set(expected) - set(decisions))} candidates missing")
    return [decisions[key] for key in expected]


def build(rows: list[dict[str, str]], inputs: dict) -> dict[Path, bytes]:
    reviewed = read_curation(rows)
    accepted = [row for row in reviewed if row["mapping_decision"] == "accept"]
    if any(row["tag_decision"] != "accept" for row in accepted):
        raise SystemExit("Every accepted new mapping must also receive an explicit computer tag decision")
    extra_count: dict[str, int] = defaultdict(int)
    expansion_rows = []
    for row in accepted:
        zh, en = row["chinese"], row["english"]
        if (zh, en) in inputs["pairs"] or zh not in inputs["pinyin"]:
            raise SystemExit(f"Accepted computerese mapping already exists or lacks pinyin: {zh} -> {en}")
        if inputs["extras"].get(zh, 0) + extra_count[zh] >= MAX_EXTRA_PER_KEY:
            raise SystemExit(f"Accepted computerese mapping exceeds per-key capacity: {zh} -> {en}")
        extra_count[zh] += 1
        expansion_rows.append({"chinese": zh, "english": en, "pos": row["pos"], "source": SOURCE})

    tag_words = {row["english"] for row in reviewed if row["tag_decision"] == "accept"}
    tag_rows = [{"english": word, "mask": str(COMPUTER_BIT), "source": SOURCE} for word in sorted(tag_words)]
    expansion_rows.sort(key=lambda row: (row["chinese"], row["english"], row["pos"]))
    mapping_bytes = write_tsv(EXPANSION, ("chinese", "english", "pos", "source"), expansion_rows, header=False)
    tag_bytes = write_tsv(TAGS, ("english", "mask", "source"), tag_rows, header=False)
    evidence_rows = []
    for row in reviewed:
        evidence_rows.append({
            **{field: row[field] for field in CANDIDATE_FIELDS},
            "mapping_decision": row["mapping_decision"],
            "tag_decision": row["tag_decision"],
            "review_note": row["review_note"],
        })
    evidence_bytes = write_tsv(EVIDENCE, CURATION_FIELDS, evidence_rows)
    current_tags = inputs["existing_computer_tags"]
    new_tag_memberships = len(tag_words - current_tags)
    base_words = inputs["words"]
    new_headwords = sorted({row["english"] for row in accepted if row["english"] not in base_words})
    manifest = {
        "batch": "20-computerese-cross-references",
        "upstream": {
            "repository": UPSTREAM,
            "commit": COMMIT,
            "commit_date": "2024-11-13",
            "license": "MIT",
            "readme_sha256": README_SHA256,
            "license_sha256": LICENSE_SHA256,
        },
        "upstream_provenance_note": "The README explicitly marks some entries as extracted from cited books. Every such footnoted row is excluded, as are long explanations; the retained short rows are candidate evidence only, not copied definitions. Each runtime mapping requires exact ECDICT gloss/POS, local pinyin, local IPA, spare capacity, and explicit review.",
        "filtered_source_terms": {
            "rows": len(read_source_terms()),
            "sha256": SOURCE_TERMS_SHA256,
            "rule": "Single English word, short Chinese gloss, no source footnote marker, no extended definition.",
        },
        "runtime_inputs_sha256": inputs["hashes"],
        "runtime_expansion_inputs": list(PREEXISTING_EXPANSIONS),
        "prior_expansion_sha256": inputs["prior_expansion_hashes"],
        "prior_computer_tag_sha256": inputs["computer_tag_hashes"],
        "candidate_pairs_with_exact_ecdict_pinyin_ipa": len(rows),
        "already_mapped_candidate_pairs": sum(row["already_mapped"] == "true" for row in rows),
        "accepted_new_mappings": len(accepted),
        "accepted_new_english_headwords": len(new_headwords),
        "new_english_headwords": new_headwords,
        "accepted_computer_tag_rows": len(tag_rows),
        "new_computer_tag_memberships": new_tag_memberships,
        "mapping_rows": [f"{row['chinese']} -> {row['english']} ({row['pos']})" for row in expansion_rows],
        "tag_rows": [row["english"] for row in tag_rows],
        "outputs": {
            EXPANSION.name: {"rows": len(expansion_rows), "sha256": sha(mapping_bytes)},
            TAGS.name: {"rows": len(tag_rows), "sha256": sha(tag_bytes)},
            EVIDENCE.relative_to(DATA).as_posix(): {"rows": len(evidence_rows), "sha256": sha(evidence_bytes)},
        },
        "runtime_note": "Only short reviewed mappings and selected computer-domain memberships enter the compiled lookup; raw upstream prose is not included in runtime data.",
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return {EXPANSION: mapping_bytes, TAGS: tag_bytes, EVIDENCE: evidence_bytes}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap-source-terms", action="store_true")
    parser.add_argument("--bootstrap-curation", action="store_true")
    parser.add_argument("--discover", action="store_true")
    args = parser.parse_args()
    if args.bootstrap_source_terms:
        bootstrap_source_terms()
        return
    inputs = load_inputs()
    rows = discover(inputs)
    if args.discover:
        print(json.dumps({
            "candidate_count": len(rows),
            "already_mapped_pairs": sum(row["already_mapped"] == "true" for row in rows),
            "new_mapping_pairs": sum(row["already_mapped"] == "false" for row in rows),
            "new_headword_candidates": len({row["english"] for row in rows if row["already_headword"] == "false" and row["already_mapped"] == "false"}),
            "new_tag_candidates": len({row["english"] for row in rows if row["already_computer_tag"] == "false"}),
        }, ensure_ascii=True, indent=2))
    elif args.bootstrap_curation:
        bootstrap_curation(rows)
    else:
        for path, content in build(rows, inputs).items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            print(f"{path.relative_to(ROOT)}: {len(content)} bytes")


if __name__ == "__main__":
    main()
