"""Build reviewed business vocabulary from the pinned Better Quant glossary."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
SOURCE_DIR = DATA / "sources/better-quant-wiki"
SNAPSHOT = SOURCE_DIR / "SNAPSHOT.json"
CURATION = DATA / "batches/17-better-quant-reviewed.tsv"
CANDIDATES = DATA / "batches/17-better-quant-candidates.tsv"
EXPANSION = DATA / "better-quant-expansion.tsv"
TAGS = DATA / "better-quant-business-tags.tsv"
MANIFEST = DATA / "better-quant-manifest.json"
UPSTREAM = "https://github.com/Tomortec/better-quant-wiki"
COMMIT = "5611485adb669828fcaf704aeb2ce9c8a86886d4"
LICENSE_SHA256 = "5c3aaa4e27ba905a388e3d20fbc11aba4e8b2f7361a56a800272e28a56d2e42a"
FILES_SHA256 = "5cff1e7fce97c7f95c372b68089c0cbd786516922a862a3a72ca15d0760bbd82"
FILE_HASHES = {
    "GLOSSARY.md": "6ce375ceac3e74a6baf4b81cc7c0e2c0b01ab9e803b9a8fea72e816413b8e068",
    "LICENSE": LICENSE_SHA256,
    "src/content/glossary/derivatives.ts": "7e67a920beff8b351330549653907c0e981fba8ac700da87d4339aaccbe30533",
    "src/content/glossary/macro.ts": "54e88656d9f33b714c5bb9bd52fc8c4a824693d93ba7d8122420734bf4369fa5",
    "src/content/glossary/markets.ts": "8be7990ba93769cb0dc442c7a9feeb98598e095689e3565c769718db93195b67",
    "src/content/glossary/pricing.ts": "abf51981863cfbdc0ccf85066f58682f8f1f39150111ad4acb0fa1f70717caf3",
    "src/content/glossary/probability.ts": "507f5087049c62926a9e8fb17421e4cd5104286e17848a88f3a758b57522959e",
    "src/content/glossary/statistics.ts": "8e0b4b82018e6d55174cc3c4c7f7f39de9d71076c0804b74f979e673ce850da4",
    "src/content/glossary/strategies.ts": "0820e414a757fab4181dfa7d0b215ba29ddf9e9d9245d787571fa0a511819582",
    "src/content/glossary/valuation.ts": "d64afbbab345d91fe4d371fe0c4320dc8655f6c1e8efdc6a2bb2e4f62379c82b",
}
BUSINESS_BIT = 1 << 7
SOURCE = "Better Quant Wiki MIT"
FIELDS = ("chinese", "english", "decision", "review_note")
ROW = re.compile(r"^\s*-\s+\[([^\]]+)\]\(([^)]+)\) \((core|supporting|context)\)$")
ACCEPTED = {"capitalization", "compounding", "drawdown", "equity", "leverage", "quotation", "security"}
EXPECTED_CANDIDATES = 41


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_snapshot() -> dict[str, str]:
    manifest = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    if (manifest.get("upstream"), manifest.get("commit"), manifest.get("license")) != (
        UPSTREAM, COMMIT, "MIT"
    ):
        raise SystemExit("Better Quant upstream pin or license changed")
    if manifest.get("files") != FILE_HASHES or manifest.get("file_count") != len(FILE_HASHES):
        raise SystemExit("Better Quant snapshot manifest changed")
    actual: dict[str, str] = {}
    for relative, expected in sorted(FILE_HASHES.items()):
        path = SOURCE_DIR / relative
        if not path.is_file() or sha(path.read_bytes()) != expected:
            raise SystemExit(f"Pinned Better Quant source changed or missing: {relative}")
        actual[relative] = expected
    canonical = "".join(f"{name}\t{digest}\n" for name, digest in actual.items())
    if sha(canonical.encode()) != FILES_SHA256 or manifest.get("files_sha256") != FILES_SHA256:
        raise SystemExit("Better Quant source snapshot digest mismatch")
    if sha((SOURCE_DIR / "LICENSE").read_bytes()) != LICENSE_SHA256:
        raise SystemExit("Better Quant MIT license changed")
    return actual


def runtime_inputs():
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.path.insert(0, str(ROOT / "build/vocabulary-research/skywind3000__ECDICT"))
    from build_professional_vocabulary import inputs

    return inputs()


def glossary_rows() -> list[dict[str, str]]:
    path = SOURCE_DIR / "GLOSSARY.md"
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if not match:
            continue
        label, url, importance = match.groups()
        parts = [part.strip() for part in label.split(" / ")]
        if len(parts) < 2:
            continue
        rows.append({
            "source_chinese": " / ".join(parts[:-1]),
            "chinese_aliases": "|".join(parts[:-1]),
            "english": parts[-1].casefold(),
            "importance": importance,
            "source_url": url,
        })
    if len(rows) != 211 or len({row["english"] for row in rows}) != 211:
        raise SystemExit(f"Expected 211 unique pinned glossary terms, got {len(rows)}")
    return rows


def source_entry_index() -> dict[tuple[str, str], tuple[str, str, str]]:
    result = {}
    for relative in FILE_HASHES:
        if not relative.endswith(".ts"):
            continue
        path = SOURCE_DIR / relative
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"(?ms)^  \{\n(?P<body>.*?)^  \},", text):
            body = match.group("body")
            slug = re.search(r'^    slug: "([^"]+)"', body, re.M)
            chinese = re.search(r'^    zh: "([^"]+)"', body, re.M)
            english = re.search(r'^    en: "([^"]+)"', body, re.M)
            definition = re.search(
                r'^    definition:\s*(?:\n\s*)?"((?:\\.|[^"])*)"', body, re.M
            )
            if slug and chinese and english and definition:
                result[(chinese.group(1), english.group(1).casefold())] = (
                    relative, slug.group(1), definition.group(1)
                )
    return result


def existing_business_terms() -> set[str]:
    result = set()
    for filename in ("professional-domain-tags.tsv", "fibo-business-tags.tsv"):
        path = DATA / filename
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            fields = line.split("\t")
            if len(fields) >= 2 and int(fields[1]) & BUSINESS_BIT:
                result.add(fields[0].casefold())
    return result


def discover() -> list[dict[str, str]]:
    verify_snapshot()
    baseline, pairs, heads, extras, pinyin, _ipa, ecdict, _ecdict_rows = runtime_inputs()
    uk = {
        line.split("\t", 1)[0].strip().casefold()
        for line in (ROOT / "pronunciation/source/en_UK.txt").read_text(encoding="utf-8").splitlines()
        if "\t" in line
    }
    us = {
        line.split("\t", 1)[0].strip().casefold()
        for line in (ROOT / "pronunciation/source/en_US.txt").read_text(encoding="utf-8").splitlines()
        if "\t" in line
    }
    pairs_lower = {(chinese, english.casefold()) for chinese, english in pairs}
    entries = source_entry_index()
    rows = []
    for row in glossary_rows():
        english = row["english"]
        source = entries.get((row["source_chinese"], english))
        if not source:
            raise SystemExit(f"No pinned Better Quant entry for {row['source_chinese']} -> {english}")
        source_file, slug, definition = source
        for chinese in row["chinese_aliases"].split("|"):
            if chinese not in pinyin:
                continue
            ecdict_pos = sorted(pos for gloss, pos in ecdict.get(english, set()) if gloss == chinese)
            rows.append({
                **row,
                "chinese": chinese,
                "pinyin": pinyin[chinese][0],
                "pinyin_frequency": str(pinyin[chinese][1]),
                "has_uk_ipa": str(english in uk).lower(),
                "has_us_ipa": str(english in us).lower(),
                "already_mapped": str((chinese, english) in pairs_lower).lower(),
                "already_headword": str(english in {word.casefold() for word in heads}).lower(),
                "existing_extra_count": str(extras[chinese]),
                "ecdict_pos_for_exact_gloss": ",".join(ecdict_pos),
                "source_file": source_file,
                "source_slug": slug,
                "definition": definition,
            })
    if EXPECTED_CANDIDATES and len(rows) != EXPECTED_CANDIDATES:
        raise SystemExit(f"Expected {EXPECTED_CANDIDATES} pinyin-reachable glossary terms, got {len(rows)}")
    return sorted(rows, key=lambda row: (row["english"], row["chinese"]))


def bootstrap_curation(rows: list[dict[str, str]]) -> None:
    if CURATION.exists():
        raise SystemExit(f"Refusing to overwrite curation: {CURATION}")
    decisions = []
    for row in rows:
        if row["already_mapped"] == "true":
            decision = "reject"
            note = "This exact Chinese-English mapping is already in the current runtime vocabulary."
        elif row["has_uk_ipa"] == "false" and row["has_us_ipa"] == "false":
            decision = "reject"
            note = "The independent pronunciation data has no whole-term IPA entry; do not create a guessed phrase pronunciation."
        elif row["english"] in ACCEPTED:
            decision = "accept"
            note = "The pinned MIT bilingual finance glossary directly defines this term; the exact Chinese candidate is pinyin-reachable and the English headword has local IPA. Add one noun sense and a business tag."
        else:
            decision = "reject"
            note = "Not selected for this small tranche; retain the source candidate for later review."
        decisions.append({"chinese": row["chinese"], "english": row["english"],
                          "decision": decision, "review_note": note})
    with CURATION.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(decisions)


def reviewed(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    expected = {(row["chinese"], row["english"]) for row in rows}
    decisions = {}
    with CURATION.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise SystemExit("Unexpected Better Quant review columns")
        for row in reader:
            key = (row["chinese"], row["english"])
            if key in decisions or key not in expected:
                raise SystemExit(f"Duplicate or stale review row: {key}")
            if row["decision"] not in {"accept", "reject"} or not row["review_note"].strip():
                raise SystemExit(f"Incomplete Better Quant review: {key}")
            decisions[key] = row
    if set(decisions) != expected:
        raise SystemExit(f"Incomplete review decisions: {len(expected - set(decisions))} missing")
    return [decisions[(row["chinese"], row["english"])] for row in rows]


def build(rows: list[dict[str, str]] | None = None) -> dict[Path, bytes]:
    source_hashes = verify_snapshot()
    rows = rows if rows is not None else discover()
    reviews = reviewed(rows)
    accepted = [row for row, decision in zip(rows, reviews) if decision["decision"] == "accept"]
    if len(accepted) != 7 or {row["english"] for row in accepted} != ACCEPTED:
        raise SystemExit("The reviewed Better Quant tranche changed; update review assertions")
    source_label = SOURCE
    expansion_rows = []
    tag_rows = []
    per_key: dict[str, int] = {}
    for row in accepted:
        chinese, english = row["chinese"], row["english"]
        if row["already_mapped"] == "true" or (row["has_uk_ipa"] == "false" and row["has_us_ipa"] == "false"):
            raise SystemExit(f"Accepted pair is already present or lacks local IPA: {chinese} -> {english}")
        per_key[chinese] = per_key.get(chinese, 0) + 1
        if int(row["existing_extra_count"]) + per_key[chinese] > 8:
            raise SystemExit(f"Expansion limit exceeded for pinyin key {chinese}")
        expansion_rows.append(f"{chinese}\t{english}\tn.\t{source_label}\n")
        tag_rows.append(f"{english}\t{BUSINESS_BIT}\t{source_label}\n")
    expansion = "".join(sorted(expansion_rows, key=str.casefold)).encode("utf-8")
    tags = "".join(sorted(tag_rows, key=str.casefold)).encode("utf-8")
    evidence_fields = (
        "chinese", "source_chinese", "chinese_aliases", "english", "importance", "source_url", "pinyin", "pinyin_frequency",
        "has_uk_ipa", "has_us_ipa", "already_mapped", "already_headword",
        "existing_extra_count", "ecdict_pos_for_exact_gloss", "source_file", "source_slug", "definition",
        "decision", "review_note",
    )
    from io import StringIO
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=evidence_fields, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for candidate, decision in zip(rows, reviews):
        writer.writerow({**candidate, **decision})
    evidence = output.getvalue().encode("utf-8")
    existing_business = existing_business_terms()
    manifest = {
        "batch": "17-better-quant-business-finance",
        "upstream": UPSTREAM,
        "commit": COMMIT,
        "license": "MIT",
        "source_file_count": len(source_hashes),
        "source_files_sha256": FILES_SHA256,
        "source_file_hashes": source_hashes,
        "source_terms": len(glossary_rows()),
        "pinyin_reachable_terms": len(rows),
        "reviewed_candidates": len(rows),
        "accepted_mappings": len(accepted),
        "new_english_headwords": sum(row["already_headword"] == "false" for row in accepted),
        "accepted_business_tag_memberships": len(accepted),
        "new_business_tag_memberships": len(set(row["english"] for row in accepted) - existing_business),
        "accepted_terms": [f"{row['chinese']} -> {row['english']}" for row in accepted],
        "expansion_sha256": sha(expansion),
        "tag_file_sha256": sha(tags),
        "evidence_file_sha256": sha(evidence),
        "curation_sha256": sha(CURATION.read_bytes()),
        "runtime_note": "Only seven reviewed bilingual mappings and their business tags enter the compact runtime index; the 211-term glossary, definitions, and review evidence remain outside the keystroke path.",
    }
    return {
        EXPANSION: expansion,
        TAGS: tags,
        CANDIDATES: evidence,
        MANIFEST: (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    }


def write_outputs(outputs: dict[Path, bytes]) -> None:
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        print(f"{path.relative_to(ROOT)}: {len(content)} bytes")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--bootstrap-curation", action="store_true")
    args = parser.parse_args()
    rows = discover()
    if args.discover:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    elif args.bootstrap_curation:
        bootstrap_curation(rows)
        print(f"Wrote {len(rows)} explicit review decisions to {CURATION.relative_to(ROOT)}")
    else:
        write_outputs(build(rows))


if __name__ == "__main__":
    main()
