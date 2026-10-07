"""Build a manually reviewed FIBO-derived business-tag tranche.

Only single-word English class labels already reachable in the local pinyin
dictionary are considered. The data source stays vendored and the small runtime
file is emitted only after every candidate has an explicit curation decision.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
SOURCE_DIR = DATA / "sources/fibo"
SNAPSHOT = SOURCE_DIR / "SNAPSHOT.json"
CURATION = DATA / "batches/16-fibo-business-reviewed.tsv"
CANDIDATES = DATA / "batches/16-fibo-business-candidates.tsv"
TAGS = DATA / "fibo-business-tags.tsv"
MANIFEST = DATA / "fibo-business-manifest.json"
UPSTREAM = "https://github.com/edmcouncil/fibo"
COMMIT = "9a7b90ccc64ef9df0762121ff058c9d27fd46037"
LICENSE_SHA256 = "59f852c87fa59411aa7dc527bd5629074d2caced7de4a48bbe7c5763359d8559"
FILES_SHA256 = "90afe310f1d3dc817c7c7f551fa0dea357ab06f6d7633c2c90897ebf1e824f7f"
FILE_COUNT = 52
BUSINESS_BIT = 1 << 7
SOURCE = "FIBO MIT"
WORD = re.compile(r"[a-z]+\Z")
FIELDS = ("headword", "decision", "review_note")
REJECT_NON_BUSINESS = {
    "civilian", "ethnicity", "government", "household", "judiciary",
    "legislature", "metal", "race",
}
REJECT_NO_DEFINITION = {
    "allocation", "announcement", "dissemination", "registration",
    "sponsor", "subscriber", "underwriting",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_snapshot() -> dict[str, str]:
    if not SNAPSHOT.is_file():
        raise SystemExit(f"Missing pinned FIBO snapshot manifest: {SNAPSHOT}")
    manifest = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    if manifest.get("upstream") != UPSTREAM or manifest.get("commit") != COMMIT:
        raise SystemExit("FIBO upstream or pinned commit changed")
    if manifest.get("license") != "MIT" or manifest.get("license_sha256") != LICENSE_SHA256:
        raise SystemExit("FIBO MIT license is missing or changed")
    license_path = SOURCE_DIR / "LICENSE"
    if not license_path.is_file() or sha(license_path.read_bytes()) != LICENSE_SHA256:
        raise SystemExit("FIBO LICENSE file is missing or changed")
    files = manifest.get("files", {})
    if len(files) != FILE_COUNT or manifest.get("file_count") != FILE_COUNT:
        raise SystemExit(f"Expected {FILE_COUNT} pinned FIBO RDF files")
    actual: dict[str, str] = {}
    for relative, expected in sorted(files.items()):
        path = SOURCE_DIR / relative
        if not path.is_file():
            raise SystemExit(f"Missing pinned FIBO file: {relative}")
        digest = sha(path.read_bytes())
        if digest != expected:
            raise SystemExit(f"Pinned FIBO file changed: {relative}")
        actual[relative] = digest
    canonical = "".join(f"{name}\t{digest}\n" for name, digest in actual.items())
    digest = sha(canonical.encode("utf-8"))
    if digest != FILES_SHA256 or manifest.get("files_sha256") != FILES_SHA256:
        raise SystemExit(f"Pinned FIBO source digest mismatch: {digest}")
    return actual


def runtime_heads() -> tuple[set[str], set[str]]:
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.path.insert(0, str(ROOT / "build/vocabulary-research/skywind3000__ECDICT"))
    from build_professional_vocabulary import inputs

    _baseline, pairs, heads, _extras, pinyin, *_rest = inputs()
    reachable = {word for chinese, word in pairs if chinese in pinyin}
    if not reachable <= heads:
        raise SystemExit("Runtime pinyin reachability is inconsistent")
    return heads, reachable


def existing_business_tags() -> set[str]:
    result = set()
    with (DATA / "professional-domain-tags.tsv").open(encoding="utf-8") as stream:
        for line in stream:
            word, mask, *_ = line.rstrip("\n").split("\t")
            if int(mask) & BUSINESS_BIT:
                result.add(word)
    return result


def discover() -> list[dict[str, str]]:
    _hashes = verify_snapshot()
    _heads, reachable = runtime_heads()
    known_business = existing_business_tags()
    RDF = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}"
    OWL = "{http://www.w3.org/2002/07/owl#}"
    RDFS = "{http://www.w3.org/2000/01/rdf-schema#}"
    XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
    classes: dict[str, dict] = {}
    for path in sorted(SOURCE_DIR.rglob("*.rdf")):
        relative = path.relative_to(SOURCE_DIR).as_posix()
        if any(token in relative.lower() for token in (
            "individual", "jurisdiction", "referenceindividual", "businesscenters",
            "regulatoryagenc",
        )):
            continue
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as error:
            raise SystemExit(f"Cannot parse pinned FIBO RDF {relative}: {error}") from error
        for element in root.iter():
            if element.tag not in (OWL + "Class", RDFS + "Class"):
                continue
            uri = element.attrib.get(RDF + "about", "")
            labels: set[str] = set()
            definitions: set[str] = set()
            for child in list(element):
                name = child.tag.rsplit("}", 1)[-1]
                language = child.attrib.get(XML_LANG, "").lower()
                if language and not language.startswith("en"):
                    continue
                if name in ("label", "prefLabel") and child.text:
                    labels.add(child.text.strip())
                elif name in ("definition", "comment") and child.text:
                    definitions.add(" ".join(child.text.split()))
            for label in labels:
                word = label.casefold()
                if not WORD.fullmatch(word) or word not in reachable:
                    continue
                row = classes.setdefault(word, {
                    "headword": word, "class_uris": set(), "source_files": set(),
                    "definitions": set(),
                })
                if uri:
                    row["class_uris"].add(uri)
                row["source_files"].add(relative)
                row["definitions"].update(definitions)

    rows = []
    for word, row in sorted(classes.items()):
        rows.append({
            "headword": word,
            "class_uris": " | ".join(sorted(row["class_uris"])),
            "source_files": ";".join(sorted(row["source_files"])),
            "definitions": " | ".join(sorted(row["definitions"])),
            "already_business_tagged": "true" if word in known_business else "false",
        })
    if len(rows) != 87:
        raise SystemExit(f"Pinned FIBO/runtime candidate count changed: expected 87, got {len(rows)}")
    return rows


def bootstrap_curation(rows: list[dict[str, str]]) -> None:
    if CURATION.exists():
        raise SystemExit(f"Curation already exists; refusing to overwrite: {CURATION}")
    decisions = []
    for row in rows:
        word = row["headword"]
        has_definition = bool(row["definitions"])
        if word in REJECT_NON_BUSINESS:
            decision = "reject"
            note = "FIBO definition is demographic, government, judicial, legislative, or physical-material vocabulary, outside this business label."
        elif word in REJECT_NO_DEFINITION or not has_definition:
            decision = "reject"
            note = "The pinned FIBO class has no English definition; keep it out of runtime until stronger evidence is available."
        else:
            decision = "accept"
            note = "FIBO defines this as a business or financial concept; the single-word headword already has a pinyin-reachable local mapping. This adds a category tag only."
        decisions.append({"headword": word, "decision": decision, "review_note": note})
    with CURATION.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(decisions)


def reviewed(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    expected = {row["headword"] for row in rows}
    if not CURATION.is_file():
        raise SystemExit(f"Missing explicit FIBO review decisions: {CURATION}")
    decisions: dict[str, dict[str, str]] = {}
    with CURATION.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if tuple(reader.fieldnames or ()) != FIELDS:
            raise SystemExit("Unexpected FIBO review columns")
        for row in reader:
            word = row["headword"]
            if word in decisions or word not in expected:
                raise SystemExit(f"Duplicate or stale FIBO review decision: {word}")
            if row["decision"] not in {"accept", "reject"} or not row["review_note"].strip():
                raise SystemExit(f"Incomplete FIBO review decision: {word}")
            decisions[word] = row
    if set(decisions) != expected:
        raise SystemExit(f"FIBO review is incomplete: {len(expected - set(decisions))} terms")
    return [decisions[row["headword"]] for row in rows]


def build() -> dict[str, bytes]:
    source_hashes = verify_snapshot()
    candidates = discover()
    reviews = reviewed(candidates)
    accepted = {row["headword"] for row in reviews if row["decision"] == "accept"}
    tag_payload = "".join(
        f"{word}\t{BUSINESS_BIT}\t{SOURCE}\n" for word in sorted(accepted)
    ).encode("utf-8")
    candidate_stream = []
    for candidate, decision in zip(candidates, reviews):
        candidate_stream.append({**candidate, **decision})
    evidence_fields = (
        "headword", "class_uris", "source_files", "definitions",
        "already_business_tagged", "decision", "review_note",
    )
    evidence_buffer = []
    from io import StringIO

    evidence_stream = StringIO(newline="")
    evidence_writer = csv.DictWriter(
        evidence_stream, fieldnames=evidence_fields, delimiter="\t", lineterminator="\n"
    )
    evidence_writer.writeheader()
    for row in candidate_stream:
        evidence_writer.writerow({field: row.get(field, "") for field in evidence_fields})
    evidence = evidence_stream.getvalue().encode("utf-8")
    tags_before = existing_business_tags()
    new_memberships = len(accepted - tags_before)
    manifest = {
        "batch": "16-fibo-business-terms",
        "upstream": UPSTREAM,
        "commit": COMMIT,
        "license": "MIT",
        "license_sha256": LICENSE_SHA256,
        "source_file_count": len(source_hashes),
        "source_files_sha256": FILES_SHA256,
        "candidate_heads": len(candidates),
        "accepted_fibo_memberships": len(accepted),
        "new_business_category_memberships": new_memberships,
        "accepted_terms": sorted(accepted),
        "tag_file_sha256": sha(tag_payload),
        "evidence_file_sha256": sha(evidence),
        "curation_sha256": sha(CURATION.read_bytes()),
        "scope_note": "Adds only a business/finance category membership to existing pinyin-reachable English headwords. It adds no Chinese-English mappings and does not change Chinese candidate order.",
    }
    return {
        TAGS: tag_payload,
        CANDIDATES: evidence,
        MANIFEST: (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    }


def write_outputs(outputs: dict[Path, bytes]) -> None:
    for path, payload in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discover", action="store_true", help="print candidates without writing runtime data")
    parser.add_argument("--bootstrap-curation", action="store_true", help="create the initial reviewed-decision TSV once")
    args = parser.parse_args()
    verify_snapshot()
    rows = discover()
    if args.discover:
        print(json.dumps({"candidate_heads": len(rows), "headwords": [row["headword"] for row in rows]}, ensure_ascii=False, indent=2))
        return
    if args.bootstrap_curation:
        bootstrap_curation(rows)
        print(f"Created {CURATION.relative_to(ROOT)} with one explicit decision per candidate")
        return
    outputs = build()
    write_outputs(outputs)
    print(json.dumps({"outputs": {path.relative_to(ROOT).as_posix(): len(data) for path, data in outputs.items()}}, indent=2))


if __name__ == "__main__":
    main()
