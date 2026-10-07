"""Build a reviewed, pinyin-reachable computer-terms tranche from a pinned source.

Candidate discovery is deterministic. Runtime mappings and tags are emitted only
when the checked-in TSV contains one explicit accept/reject decision per candidate.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
SOURCE_DIR = DATA / "sources/cjk-compsci-terms"
TABLES = SOURCE_DIR / "tables"
CURATION = DATA / "batches/15-cjk-compsci-reviewed.tsv"
CANDIDATES = DATA / "batches/15-cjk-compsci-candidates.tsv"
EVIDENCE = DATA / "batches/15-cjk-compsci-evidence.tsv"
TAGS = DATA / "cjk-compsci-tags.tsv"
EXPANSION = DATA / "cjk-compsci-expansion.tsv"
MANIFEST = DATA / "cjk-compsci-manifest.json"
UPSTREAM = "https://github.com/dahlia/cjk-compsci-terms"
COMMIT = "3cf825e81375202fd408427933c3a30442defa4f"
LICENSE_SHA256 = "21617ba96327d3f8d69c639439cbc95ec156c304250f835ea6a2ecd94dfcab88"
TABLES_SHA256 = "5a4eca03b0de8404b8b21b1278ba68aa8e212a50753ab9af71d10b50ceaabf39"
INPUTS = {
    "pinyin": (ROOT / "build/pinyin-candidates.tsv", "914f6894fff1f6033af6d8bb9858f6901aa2d1a960cd2afd8923f899584f1290"),
    "baseline": (ROOT / "build/expansion-base.tsv", "ed58a90825243beada4d759f2f90d55ccdb4d38fc8701dffd78090e3a0b21d35"),
    "ecdict": (ROOT / "build/vocabulary-research/skywind3000__ECDICT/ecdict.csv", "1a6947e04785db63613a92e14903cdae7954f7e84860b10e68e5c7cbb3f9c3cf"),
    "uk_ipa": (ROOT / "pronunciation/source/en_UK.txt", "221394caef0cf723b4f2df81a98ac33191293257b88aed5b1fb89466d3a0dc77"),
    "us_ipa": (ROOT / "pronunciation/source/en_US.txt", "2af6f154a5c363275f052d1f85acedef38ed185ca9745aa4314be77f6b70de67"),
}
SOURCE = "CJK computer science terms CC BY-SA 4.0"
DOMAIN_BIT = 1 << 6
MAX_EXTRA_PER_KEY = 8
WORD = re.compile(r"[a-z]+(?:[-'][a-z]+)*\Z")
_RUNTIME_CACHE = None
FIELDS = (
    "chinese", "english", "pinyin", "pinyin_frequency", "ipa_sources",
    "ecdict_pos", "ecdict_exact_pos", "source_tables", "source_correspondence",
    "pos", "review_decision", "review_note",
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_hashes() -> tuple[dict[str, str], str]:
    paths = sorted(TABLES.glob("*.yaml"))
    if len(paths) != 28:
        raise SystemExit(f"Expected 28 pinned upstream tables, found {len(paths)}")
    hashes = {path.name: sha(path.read_bytes()) for path in paths}
    canonical = "".join(f"tables/{name}\t{digest}\n" for name, digest in hashes.items())
    return hashes, sha(canonical.encode("utf-8"))


def verify_inputs() -> dict[str, str]:
    actual: dict[str, str] = {}
    for name, (path, expected) in INPUTS.items():
        if not path.is_file():
            raise SystemExit(f"Missing pinned input: {path}")
        actual[name] = sha(path.read_bytes())
        if actual[name] != expected:
            raise SystemExit(f"Pinned {name} SHA-256 mismatch: {actual[name]}")
    license_file = SOURCE_DIR / "LICENSE"
    if not license_file.is_file() or sha(license_file.read_bytes()) != LICENSE_SHA256:
        raise SystemExit("Pinned upstream CC BY-SA license file is missing or changed")
    _hashes, table_digest = source_hashes()
    if table_digest != TABLES_SHA256:
        raise SystemExit(f"Pinned upstream table SHA-256 mismatch: {table_digest}")
    actual["upstream_tables"] = table_digest
    actual["upstream_license"] = LICENSE_SHA256
    return actual


def runtime_inputs():
    global _RUNTIME_CACHE
    if _RUNTIME_CACHE is not None:
        return _RUNTIME_CACHE
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.path.insert(0, str(ROOT / "build/vocabulary-research/skywind3000__ECDICT"))
    from build_professional_vocabulary import inputs as load_inputs
    from build_wiktionary_expansion import read_expansion
    from opencc import OpenCC
    baseline, pairs, words, extras, pinyin, _ipa, ecdict, ecdict_rows = load_inputs()
    # Batch 14 is a preceding, separately licensed source and must count toward
    # current exact mappings and the per-Chinese-key expansion ceiling.
    for row in read_expansion(DATA / "professional-expansion.tsv"):
        pairs.add((row["chinese"], row["english"]))
        words.add(row["english"])
        extras[row["chinese"]] += 1
    ipa_sources: dict[str, set[str]] = collections.defaultdict(set)
    for label, key in (("UK", "uk_ipa"), ("US", "us_ipa")):
        path = INPUTS[key][0]
        for line in path.read_text(encoding="utf-8").splitlines():
            if "\t" in line:
                ipa_sources[line.split("\t", 1)[0].strip().casefold()].add(label)
    _RUNTIME_CACHE = OpenCC("t2s"), pairs, words, extras, pinyin, ipa_sources, ecdict, ecdict_rows
    return _RUNTIME_CACHE


def discover() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    import yaml

    converter, pairs, words, extras, pinyin, ipa_sources, ecdict, ecdict_rows = runtime_inputs()
    existing_direct: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    candidates: dict[tuple[str, str], dict[str, set[str] | str]] = {}
    for path in sorted(TABLES.glob("*.yaml")):
        for record in yaml.safe_load(path.read_text(encoding="utf-8")) or []:
            english_terms = [str(term).strip().casefold() for term in (record.get("en") or {})]
            for raw_chinese, components in (record.get("zh-CN") or {}).items():
                chinese = converter.convert(str(raw_chinese)).strip()
                if not chinese or chinese not in pinyin:
                    continue
                correspondence = " ".join(
                    str(component.get("correspond", "")).strip().casefold()
                    for component in components if component.get("correspond")
                ).strip()
                # For tags on mappings already in the runtime, require the source's
                # explicit semantic component links to reconstruct the English term.
                normalized_correspondence = re.sub(r"[^a-z0-9]", "", correspondence)
                for english in english_terms:
                    if normalized_correspondence and normalized_correspondence == re.sub(r"[^a-z0-9]", "", english):
                        if (chinese, english) in pairs:
                            existing_direct[(chinese, english)].add(path.stem)

                # Each source table is a translation record, but component-level
                # correspondences can distinguish false friends. We retain all
                # pinyin-reachable single-word entries for explicit human review.
                for english in english_terms:
                    if not WORD.fullmatch(english) or english not in ipa_sources or not ecdict.get(english):
                        continue
                    if (chinese, english) in pairs or extras[chinese] >= MAX_EXTRA_PER_KEY:
                        continue
                    key = (chinese, english)
                    row = candidates.setdefault(key, {
                        "chinese": chinese, "english": english,
                        "pinyin": pinyin[chinese][0], "pinyin_frequency": str(pinyin[chinese][1]),
                        "ipa_sources": set(), "ecdict_pos": set(), "ecdict_exact_pos": set(),
                        "source_tables": set(), "source_correspondence": set(),
                    })
                    row["ipa_sources"].update(ipa_sources[english])
                    row["ecdict_pos"].update(pos for _, pos in ecdict[english])
                    row["ecdict_exact_pos"].update(pos for gloss, pos in ecdict[english] if gloss == chinese)
                    row["source_tables"].add(path.stem)
                    row["source_correspondence"].add(correspondence or "(no component gloss)")

    rows = []
    for key in sorted(candidates):
        row = candidates[key]
        rows.append({field: ",".join(sorted(row[field])) if isinstance(row[field], set) else str(row[field])
                     for field in ("chinese", "english", "pinyin", "pinyin_frequency", "ipa_sources",
                                   "ecdict_pos", "ecdict_exact_pos", "source_tables", "source_correspondence")})
    evidence = []
    for (chinese, english), tables in sorted(existing_direct.items()):
        evidence.append({
            "chinese": chinese, "english": english, "status": "existing-exact-correspondence",
            "source_tables": ",".join(sorted(tables)), "pinyin": pinyin[chinese][0],
            "pinyin_frequency": str(pinyin[chinese][1]), "source": SOURCE,
        })
    return rows, evidence


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


def read_curation(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    if not CURATION.is_file():
        raise SystemExit("Missing explicit review decisions: " + str(CURATION))
    expected = {(row["chinese"], row["english"]): row for row in candidates}
    reviewed: list[dict[str, str]] = []
    seen = set()
    with CURATION.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise SystemExit("Unexpected CJK computer-science curation columns")
        for row in reader:
            key = (row["chinese"], row["english"])
            if key in seen or key not in expected:
                raise SystemExit("Duplicate or stale CJK computer-science decision: " + repr(key))
            seen.add(key)
            source_row = expected[key]
            for field in FIELDS[:9]:
                if row[field] != source_row[field]:
                    raise SystemExit(f"CJK source evidence changed for {key}: {field}")
            pos_options = set(row["ecdict_pos"].split(","))
            if row["pos"] not in pos_options:
                raise SystemExit(f"Selected POS is absent from ECDICT for {key}: {row['pos']}")
            if row["review_decision"] not in {"accept", "reject"} or not row["review_note"].strip():
                raise SystemExit("Every CJK candidate requires a decision and note: " + repr(key))
            reviewed.append(row)
    if seen != set(expected):
        raise SystemExit(f"Incomplete CJK review: {len(set(expected) - seen)} candidates remain")
    return reviewed


def build() -> dict[Path, bytes]:
    hashes = verify_inputs()
    candidates, existing_evidence = discover()
    reviewed = read_curation(candidates)
    accepted = [row for row in reviewed if row["review_decision"] == "accept"]
    previously_mapped_words = runtime_inputs()[2]
    new_headwords = sorted({row["english"] for row in accepted if row["english"] not in previously_mapped_words})
    tags: dict[str, int] = collections.defaultdict(int)
    for row in existing_evidence:
        tags[row["english"]] |= DOMAIN_BIT
    for row in accepted:
        tags[row["english"]] |= DOMAIN_BIT
    tag_rows = [{"english": word, "mask": str(mask), "source": SOURCE} for word, mask in sorted(tags.items())]
    expansion_rows = [{"chinese": row["chinese"], "english": row["english"], "pos": row["pos"], "source": SOURCE}
                      for row in sorted(accepted, key=lambda item: (item["chinese"], item["english"]))]
    evidence = existing_evidence + [{
        "chinese": row["chinese"], "english": row["english"], "status": "accepted" if row["review_decision"] == "accept" else "rejected",
        "source_tables": row["source_tables"], "pinyin": row["pinyin"],
        "pinyin_frequency": row["pinyin_frequency"], "source": SOURCE,
        "review_note": row["review_note"],
    } for row in reviewed]
    evidence.sort(key=lambda item: (item["chinese"], item["english"], item["status"]))

    tag_bytes = write_tsv(TAGS, ("english", "mask", "source"), tag_rows, header=False)
    expansion_bytes = write_tsv(EXPANSION, ("chinese", "english", "pos", "source"), expansion_rows, header=False)
    evidence_bytes = write_tsv(EVIDENCE, ("chinese", "english", "status", "source_tables", "pinyin", "pinyin_frequency", "source", "review_note"), evidence)
    curation_bytes = CURATION.read_bytes()
    hashes.update({"curation": sha(curation_bytes)})
    manifest = {
        "batch": "15-cjk-computer-science-terms",
        "upstream": {"repository": UPSTREAM, "commit": COMMIT, "license": "CC BY-SA 4.0",
                     "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
                     "tables": 28, "tables_sha256": hashes["upstream_tables"],
                     "license_sha256": hashes["upstream_license"]},
        "input_sha256": hashes,
        "review": {"candidate_mappings": len(candidates),
                   "accepted_mappings": len(accepted),
                   "rejected_mappings": len(reviewed) - len(accepted),
                   "new_headwords": len(new_headwords),
                   "new_headword_list": new_headwords,
                   "curation_file": CURATION.relative_to(DATA).as_posix()},
        "outputs": {
            TAGS.name: {"rows": len(tag_rows), "sha256": sha(tag_bytes)},
            EXPANSION.name: {"rows": len(expansion_rows), "sha256": sha(expansion_bytes)},
            EVIDENCE.relative_to(DATA).as_posix(): {"rows": len(evidence), "sha256": sha(evidence_bytes)},
        },
        "modifications": "Retained only simplified Chinese terms on the exact local pinyin candidate surface. Existing mappings receive a computer-domain tag only when source component correspondences reconstruct the English term. New single-word candidates require local IPA, an ECDICT POS record, spare per-key capacity, and explicit human review. Added mappings are separate from the upstream source tables.",
        "scope_note": "An audited reachable subset of a community computer-science comparison glossary, not a complete computer curriculum.",
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    MANIFEST.write_bytes(manifest_bytes)
    return {TAGS: tag_bytes, EXPANSION: expansion_bytes, EVIDENCE: evidence_bytes, MANIFEST: manifest_bytes}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discover", action="store_true", help="write review candidates only; do not touch runtime outputs")
    args = parser.parse_args()
    verify_inputs()
    candidates, _evidence = discover()
    if args.discover:
        payload = write_tsv(CANDIDATES, FIELDS[:9], candidates)
        print(f"Discovered {len(candidates)} review candidates; SHA-256 {sha(payload)}")
        return
    outputs = build()
    print(json.dumps({path.name: len(data) for path, data in outputs.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
