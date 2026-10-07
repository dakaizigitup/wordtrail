"""Build a reviewed life-science vocabulary tranche from pinned NAER open data."""
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
SOURCE_CSV = DATA / "sources/naer/life-science-academic-terms.csv"
SOURCE_METADATA = DATA / "sources/naer/life-science-dataset.json"
SOURCE_SHA256 = "d8d00e504e1e5feeeb5cad1464c1a1806963689dc43b398594d9e5bdce1556f0"
METADATA_SHA256 = "bb31ed9b21f3e67f6a03458284030820ceb0166fa7f83313905207c141074285"
PREFILTER = DATA / "batches/26-naer-life-science-prefilter.tsv"
CANDIDATES = DATA / "batches/26-naer-life-science-candidates.tsv"
REVIEWED = DATA / "batches/26-naer-life-science-reviewed.tsv"
EXPANSION = DATA / "naer-life-science-expansion.tsv"
TAGS = DATA / "naer-life-science-tags.tsv"
MANIFEST = DATA / "naer-life-science-manifest.json"

SOURCE = "NAER Life Science Academic Terms OGDL v1.0"
MEDICAL_BIT = 1 << 8
WORD = re.compile(r"[a-z][a-z'-]*\Z")
EN_SEPARATORS = re.compile(r"[;；]+")
ZH_SEPARATORS = re.compile(r"[；;、，,/／|]+")

PREFILTER_FIELDS = (
    "english", "chinese", "source_chinese", "source_records", "source_url_field",
    "domain", "pinyin", "pinyin_frequency", "ipa_sources", "noun_evidence",
    "ecdict_exact_noun_gloss", "mesh_ids", "mesh_preferred_terms", "mesh_tree_numbers",
    "already_mapped", "existing_headword", "existing_medical_tag", "spare_capacity",
)
REVIEW_FIELDS = PREFILTER_FIELDS + ("decision", "review_note")

# Deliberately small: retain medical / clinical / biomedical terms; do not turn
# the general life-science taxonomy into a medical tag by source label alone.
ACCEPTED = {
    ("交媾", "coitus"): "Official life-science bilingual entry; exact ECDICT noun gloss and MeSH Coitus support the medical/reproductive sense.",
    ("射精", "ejaculation"): "Exact clinical/reproductive term, exact ECDICT noun gloss, and MeSH Ejaculation; new IPA-backed headword.",
    ("发炎", "inflammation"): "Widely used concise Chinese rendering of inflammation; exact ECDICT noun gloss and MeSH term support it.",
    ("结扎", "ligation"): "Exact clinical procedure term; source, ECDICT noun gloss, and MeSH Ligation agree.",
    ("麻痹", "paralysis"): "Accepted Chinese clinical sense of paralysis; local ECDICT lists it as an exact noun gloss.",
    ("知觉", "perception"): "Direct psychological/clinical noun sense; exact ECDICT gloss and MeSH Perception agree.",
    ("繁殖", "reproduction"): "Direct biological reproductive process; exact ECDICT noun gloss and MeSH Reproduction agree.",
}

REJECTED = {
    ("酒精", "ethanol"): "酒精 is broader than ethanol; the precise chemical term is 乙醇, so do not add the broader source gloss as a standalone mapping.",
    ("发芽", "germination"): "Accurate plant-biology term, but outside the medical category supported by this tranche.",
    ("交尾", "copulation"): "Accurate animal-biology sense, but not retained in the medical translation category.",
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


def load_inputs():
    if sha(SOURCE_CSV.read_bytes()) != SOURCE_SHA256:
        raise SystemExit("Pinned NAER life-science CSV SHA-256 mismatch")
    metadata_bytes = SOURCE_METADATA.read_bytes()
    if sha(metadata_bytes) != METADATA_SHA256:
        raise SystemExit("Pinned NAER life-science metadata SHA-256 mismatch")
    metadata = json.loads(metadata_bytes.decode("utf-8-sig"))
    if metadata.get("dataset_id") != "15213" or metadata.get("snapshot_sha256") != SOURCE_SHA256:
        raise SystemExit("Unexpected NAER life-science dataset metadata")

    sys.path.insert(0, str(ROOT / "build/vocab-tools"))
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_naer_medical_batch_2 as naer_batch

    inputs, term_index, descriptors, base_manifest = naer_batch.load_inputs()
    # Batch 25 is newer than the frozen baseline used by batch 24/25 builders.
    for line in (DATA / "naer-medical-expansion-2.tsv").read_text(encoding="utf-8").splitlines():
        chinese, english, _pos, _origin = line.split("\t")
        pair = (chinese, english.casefold())
        if pair not in inputs["pairs"]:
            inputs["pairs"].add(pair)
            inputs["extras"][chinese] = inputs["extras"].get(chinese, 0) + 1
        inputs["words"].add(english.casefold())
    for line in (DATA / "naer-medical-tags-2.tsv").read_text(encoding="utf-8").splitlines():
        inputs["existing_medical_tags"].add(line.split("\t", 1)[0].casefold())
    return inputs, term_index, descriptors, base_manifest


def discover(inputs, term_index, descriptors):
    from opencc import OpenCC

    converter = OpenCC("t2s")
    ipa_words = inputs["uk"] | inputs["us"]
    prefilter: dict[tuple[str, str], dict[str, str]] = {}
    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        expected = ("序號", "英文名稱", "中文名稱", "學門", "來源網站")
        if tuple(reader.fieldnames or ()) != expected:
            raise SystemExit(f"Unexpected NAER life-science columns: {reader.fieldnames}")
        for row in reader:
            for raw_english in EN_SEPARATORS.split(row["英文名稱"].strip()):
                english = raw_english.strip().casefold()
                if not WORD.fullmatch(english) or english not in ipa_words:
                    continue
                noun_glosses = sorted({
                    converter.convert(gloss).strip()
                    for gloss, pos in inputs["ecdict"].get(english, ())
                    if pos == "n."
                })
                if not noun_glosses:
                    continue
                mesh = term_index.get(english, {"ids": set(), "preferred": set(), "trees": set()})
                mesh_ids = sorted(mid for mid in mesh["ids"] if mid in descriptors
                                  and descriptors[mid]["english"].casefold() == english)
                if not mesh_ids:
                    continue
                mesh_trees = sorted({tree for mid in mesh_ids
                                     for tree in descriptors[mid]["tree_numbers"].split(",") if tree})
                for raw_chinese in ZH_SEPARATORS.split(row["中文名稱"].strip()):
                    chinese = converter.convert(raw_chinese.strip()).strip()
                    if not chinese or chinese not in inputs["pinyin"] or chinese not in noun_glosses:
                        continue
                    pair = (chinese, english)
                    if pair in prefilter:
                        prior = prefilter[pair]
                        prior["source_records"] = ",".join(sorted(
                            set(prior["source_records"].split(",")) | {row["序號"].strip()}, key=int
                        ))
                        prior["source_url_field"] = " | ".join(sorted(set(prior["source_url_field"].split(" | ")) | {row["來源網站"].strip()}))
                        continue
                    pinyin, frequency = inputs["pinyin"][chinese]
                    prefilter[pair] = {
                        "english": english,
                        "chinese": chinese,
                        "source_chinese": row["中文名稱"].strip(),
                        "source_records": row["序號"].strip(),
                        "source_url_field": row["來源網站"].strip(),
                        "domain": row["學門"].strip(),
                        "pinyin": pinyin,
                        "pinyin_frequency": str(frequency),
                        "ipa_sources": ",".join(name for name, words in (("UK", inputs["uk"]), ("US", inputs["us"])) if english in words),
                        "noun_evidence": "ECDICT n.",
                        "ecdict_exact_noun_gloss": chinese,
                        "mesh_ids": ",".join(mesh_ids),
                        "mesh_preferred_terms": " | ".join(sorted({descriptors[mid]["english"] for mid in mesh_ids})),
                        "mesh_tree_numbers": ",".join(mesh_trees),
                        "already_mapped": str(pair in inputs["pairs"]).lower(),
                        "existing_headword": str(english in inputs["words"]).lower(),
                        "existing_medical_tag": str(english in inputs["existing_medical_tags"]).lower(),
                        "spare_capacity": str(inputs["extras"].get(chinese, 0) < 8).lower(),
                    }
    rows = sorted(prefilter.values(), key=lambda r: (r["english"], r["chinese"], r["source_records"]))
    candidates = [row for row in rows if row["already_mapped"] == "false" and row["spare_capacity"] == "true"]
    return rows, candidates


def review(candidates: list[dict[str, str]]):
    reviewed = []
    seen = set()
    for row in candidates:
        key = (row["chinese"], row["english"])
        if key in seen:
            raise SystemExit(f"Duplicate NAER life-science candidate: {key}")
        seen.add(key)
        if key in ACCEPTED:
            decision, note = "accept", ACCEPTED[key]
        elif key in REJECTED:
            decision, note = "reject", REJECTED[key]
        else:
            decision = "defer"
            note = "官方生命科学英中对照与本机读音、拼音和词性均匹配，但本批未确认其适合独立医学译词；暂不加入。"
        reviewed.append({**row, "decision": decision, "review_note": note})
    missing = (set(ACCEPTED) | set(REJECTED)) - seen
    if missing:
        raise SystemExit(f"Curated NAER life-science decisions absent from candidates: {sorted(missing)}")
    return reviewed


def build(prefilter, candidates, reviewed, inputs, term_index, base_manifest):
    accepted = [row for row in reviewed if row["decision"] == "accept"]
    rejected = [row for row in reviewed if row["decision"] == "reject"]
    deferred = [row for row in reviewed if row["decision"] == "defer"]
    per_key = Counter(row["chinese"] for row in accepted)
    for chinese, count in per_key.items():
        if inputs["extras"].get(chinese, 0) + count > 8:
            raise SystemExit(f"Accepted mappings exceed per-key cap: {chinese}")
    expansion_rows = [
        {"chinese": row["chinese"], "english": row["english"], "pos": "n.", "source": SOURCE}
        for row in accepted
    ]
    expansion_rows.sort(key=lambda row: (row["chinese"], row["english"]))
    new_headwords = sorted({row["english"] for row in accepted if row["english"] not in inputs["words"]})
    tag_words = sorted({row["english"] for row in accepted if row["english"] not in inputs["existing_medical_tags"]})
    tag_rows = [{"english": word, "mask": str(MEDICAL_BIT), "source": SOURCE} for word in tag_words]
    prefilter_bytes = write_tsv(PREFILTER, PREFILTER_FIELDS, prefilter)
    candidate_bytes = write_tsv(CANDIDATES, PREFILTER_FIELDS, candidates)
    reviewed_bytes = write_tsv(REVIEWED, REVIEW_FIELDS, reviewed)
    expansion_bytes = write_tsv(EXPANSION, ("chinese", "english", "pos", "source"), expansion_rows, header=False)
    tag_bytes = write_tsv(TAGS, ("english", "mask", "source"), tag_rows, header=False)
    source_hashes = {
        SOURCE_CSV.name: SOURCE_SHA256,
        SOURCE_METADATA.name: METADATA_SHA256,
        "naer-medical-expansion.tsv": sha((DATA / "naer-medical-expansion.tsv").read_bytes()),
        "naer-medical-expansion-2.tsv": sha((DATA / "naer-medical-expansion-2.tsv").read_bytes()),
        "naer-medical-tags-2.tsv": sha((DATA / "naer-medical-tags-2.tsv").read_bytes()),
        **base_manifest["source_hashes"],
    }
    manifest = {
        "batch": "26-naer-life-science",
        "source": {
            "title": "National Academy for Educational Research - Terminology of Life Science",
            "dataset_url": "https://data.gov.tw/en/datasets/15213",
            "license": "Open Government Data License v1.0",
            "license_url": "https://data.gov.tw/license",
            "portal_last_updated": "2026-08-12 16:00",
            "snapshot_sha256": SOURCE_SHA256,
        },
        "filters": {
            "source_scope": "Single-word English terms with local IPA, exact ECDICT noun gloss, reachable pinyin, and exact preferred MeSH 2026 descriptor.",
            "candidate_scope": "New mappings with available per-key capacity, individually reviewed for medical/biomedical relevance.",
            "runtime_per_key_cap": 8,
            "traditional_to_simplified": "OpenCC t2s",
        },
        "counts": {
            "source_records": sum(1 for _ in SOURCE_CSV.open(encoding="utf-8-sig")) - 1,
            "eligible_source_pairs": len(prefilter),
            "already_mapped_pairs": sum(row["already_mapped"] == "true" for row in prefilter),
            "new_candidates": len(candidates),
            "accepted_mappings": len(accepted),
            "rejected_candidates": len(rejected),
            "deferred_candidates": len(deferred),
            "new_english_headwords": len(new_headwords),
            "new_medical_tag_memberships": len(tag_words),
        },
        "source_hashes": source_hashes,
        "outputs": {
            PREFILTER.name: sha(prefilter_bytes),
            CANDIDATES.name: sha(candidate_bytes),
            REVIEWED.name: sha(reviewed_bytes),
            EXPANSION.name: sha(expansion_bytes),
            TAGS.name: sha(tag_bytes),
        },
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    inputs, term_index, descriptors, base_manifest = load_inputs()
    prefilter, candidates = discover(inputs, term_index, descriptors)
    reviewed = review(candidates)
    manifest = build(prefilter, candidates, reviewed, inputs, term_index, base_manifest)
    print(json.dumps(manifest["counts"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
