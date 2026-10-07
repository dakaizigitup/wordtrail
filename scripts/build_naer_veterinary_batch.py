"""Build a reviewed veterinary-medical vocabulary tranche from NAER open data."""
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
SOURCE_CSV = DATA / "sources/naer/veterinary-academic-terms.csv"
SOURCE_METADATA = DATA / "sources/naer/veterinary-dataset.json"
SOURCE_SHA256 = "cc4599654cbf83fca9ec02b411f08cae8d4d8026925177477c26b97c30837863"
METADATA_SHA256 = "b73c4bf5db9d1e8ecc65b743ca739c1e0cdaeead99e85d8cba62a9802a80bb1e"
PREFILTER = DATA / "batches/27-naer-veterinary-prefilter.tsv"
CANDIDATES = DATA / "batches/27-naer-veterinary-candidates.tsv"
REVIEWED = DATA / "batches/27-naer-veterinary-reviewed.tsv"
EXPANSION = DATA / "naer-veterinary-expansion.tsv"
TAGS = DATA / "naer-veterinary-tags.tsv"
MANIFEST = DATA / "naer-veterinary-manifest.json"

SOURCE = "NAER Veterinary Medical Terms OGDL v1.0"
MEDICAL_BIT = 1 << 8
WORD = re.compile(r"[a-z][a-z'-]*\Z")
EN_SEPARATORS = re.compile(r"[;；]+")
ZH_SEPARATORS = re.compile(r"[；;、，,/／|]+")

PREFILTER_FIELDS = (
    "english", "chinese", "source_chinese", "source_records", "source_url_field",
    "pinyin", "pinyin_frequency", "ipa_sources", "noun_evidence",
    "ecdict_exact_noun_gloss", "mesh_ids", "mesh_preferred_terms", "mesh_tree_numbers",
    "already_mapped", "existing_headword", "existing_medical_tag", "spare_capacity",
)
REVIEW_FIELDS = PREFILTER_FIELDS + ("decision", "review_note")

ACCEPTED = {
    ("发烧", "fever"): "Common Chinese term for fever; exact ECDICT noun gloss and MeSH Fever support this clinical sense.",
    ("增殖", "hyperplasia"): "Exact pathology term; local ECDICT noun gloss and MeSH Hyperplasia agree.",
    ("肥胖", "obesity"): "Exact clinical condition; source, ECDICT noun gloss, and MeSH Obesity agree.",
    ("苍白", "pallor"): "Direct clinical sign; exact ECDICT noun gloss and MeSH Pallor support this new IPA-backed headword.",
    ("酗酒", "alcoholism"): "Accepted common clinical rendering; exact local ECDICT noun gloss and MeSH Alcoholism support it.",
    ("瘫痪", "paralysis"): "Direct Chinese clinical term for paralysis; exact ECDICT noun gloss and MeSH Paralysis support this additional sense.",
}

REJECTED = {
    ("扁桃体", "amygdala"): "This is a false friend: 扁桃体 means tonsil; amygdala is 杏仁核/杏仁体.",
    ("麻木", "anesthesia"): "麻木 means numbness; anesthesia is more precisely 麻醉, so the source gloss is too broad here.",
    ("冻疮", "frostbite"): "冻疮 is chilblains/pernio; frostbite is 冻伤, a different condition.",
    ("蒸发", "exhalation"): "蒸发 means evaporation; exhalation is 呼气/呼出, so this is a mismatched translation.",
    ("阻碍", "embarrassment"): "阻碍 is not the meaning of embarrassment; reject the source pair as a false match.",
    ("鼻毛", "vibrissae"): "Vibrissae are specialized tactile whiskers; 鼻毛 is narrower and may not preserve the term's veterinary meaning.",
    ("粉末", "dust"): "The gloss is too broad and general for a useful veterinary medical translation.",
    ("焚化", "incineration"): "Environmental/waste-processing term, outside the veterinary-medical tag scope of this tranche.",
    ("烟雾", "smog"): "Environmental term, outside the veterinary-medical tag scope of this tranche.",
    ("发芽", "germination"): "Plant-biology term, outside the veterinary-medical tag scope of this tranche.",
    ("蒸馏", "distillation"): "General chemistry process, not retained as a veterinary-medical term in this tranche.",
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
        raise SystemExit("Pinned NAER veterinary CSV SHA-256 mismatch")
    metadata_bytes = SOURCE_METADATA.read_bytes()
    if sha(metadata_bytes) != METADATA_SHA256:
        raise SystemExit("Pinned NAER veterinary metadata SHA-256 mismatch")
    metadata = json.loads(metadata_bytes.decode("utf-8-sig"))
    if metadata.get("dataset_id") != "15461" or metadata.get("snapshot_sha256") != SOURCE_SHA256:
        raise SystemExit("Unexpected NAER veterinary dataset metadata")

    sys.path.insert(0, str(ROOT / "build/vocab-tools"))
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_naer_life_science_batch as life_batch

    inputs, term_index, descriptors, medical_manifest = life_batch.load_inputs()
    # Include the accepted mappings and category members from batch 26.
    for line in (DATA / "naer-life-science-expansion.tsv").read_text(encoding="utf-8").splitlines():
        chinese, english, _pos, _origin = line.split("\t")
        pair = (chinese, english.casefold())
        if pair not in inputs["pairs"]:
            inputs["pairs"].add(pair)
            inputs["extras"][chinese] = inputs["extras"].get(chinese, 0) + 1
        inputs["words"].add(english.casefold())
    for line in (DATA / "naer-life-science-tags.tsv").read_text(encoding="utf-8").splitlines():
        inputs["existing_medical_tags"].add(line.split("\t", 1)[0].casefold())
    return inputs, term_index, descriptors, medical_manifest


def discover(inputs, term_index, descriptors):
    from opencc import OpenCC

    converter = OpenCC("t2s")
    ipa_words = inputs["uk"] | inputs["us"]
    collected: dict[tuple[str, str], dict[str, str]] = {}
    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        expected = ("序號", "英文名稱", "中文名稱", "來源網站")
        if tuple(reader.fieldnames or ()) != expected:
            raise SystemExit(f"Unexpected NAER veterinary columns: {reader.fieldnames}")
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
                    pinyin, frequency = inputs["pinyin"][chinese]
                    candidate = {
                        "english": english,
                        "chinese": chinese,
                        "source_chinese": row["中文名稱"].strip(),
                        "source_records": row["序號"].strip(),
                        "source_url_field": row["來源網站"].strip(),
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
                    prior = collected.get(pair)
                    if prior:
                        prior["source_records"] = ",".join(sorted(
                            set(prior["source_records"].split(",")) | {row["序號"].strip()}, key=int
                        ))
                        prior["source_url_field"] = " | ".join(sorted(set(prior["source_url_field"].split(" | ")) | {row["來源網站"].strip()}))
                    else:
                        collected[pair] = candidate
    rows = sorted(collected.values(), key=lambda r: (r["english"], r["chinese"], r["source_records"]))
    candidates = [row for row in rows if row["already_mapped"] == "false" and row["spare_capacity"] == "true"]
    return rows, candidates


def review(candidates: list[dict[str, str]]):
    reviewed = []
    seen = set()
    for row in candidates:
        key = (row["chinese"], row["english"])
        if key in seen:
            raise SystemExit(f"Duplicate NAER veterinary candidate: {key}")
        seen.add(key)
        if key in ACCEPTED:
            decision, note = "accept", ACCEPTED[key]
        elif key in REJECTED:
            decision, note = "reject", REJECTED[key]
        else:
            decision = "defer"
            note = "官方獸醫學英中對照、ECDICT名詞義與 MeSH 詞條可核驗，但本批未確認其是否為合適的獨立醫學譯詞；暫緩。"
        reviewed.append({**row, "decision": decision, "review_note": note})
    missing = (set(ACCEPTED) | set(REJECTED)) - seen
    if missing:
        raise SystemExit(f"Curated NAER veterinary decisions absent from candidates: {sorted(missing)}")
    return reviewed


def build(prefilter, candidates, reviewed, inputs, base_manifest):
    accepted = [row for row in reviewed if row["decision"] == "accept"]
    rejected = [row for row in reviewed if row["decision"] == "reject"]
    deferred = [row for row in reviewed if row["decision"] == "defer"]
    per_key = Counter(row["chinese"] for row in accepted)
    for chinese, count in per_key.items():
        if inputs["extras"].get(chinese, 0) + count > 8:
            raise SystemExit(f"Accepted veterinary mappings exceed per-key cap: {chinese}")
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
        "naer-life-science-expansion.tsv": sha((DATA / "naer-life-science-expansion.tsv").read_bytes()),
        "naer-life-science-tags.tsv": sha((DATA / "naer-life-science-tags.tsv").read_bytes()),
        **base_manifest["source_hashes"],
    }
    manifest = {
        "batch": "27-naer-veterinary-medical",
        "source": {
            "title": "National Academy for Educational Research - Veterinary Medical Terminology",
            "dataset_url": "https://data.gov.tw/en/datasets/15461",
            "license": "Open Government Data License v1.0",
            "license_url": "https://data.gov.tw/license",
            "portal_last_updated": "2026-06-01 14:43",
            "snapshot_sha256": SOURCE_SHA256,
        },
        "filters": {
            "source_scope": "Single-word English terms with local IPA, exact ECDICT noun gloss, reachable pinyin, and exact preferred MeSH 2026 descriptor.",
            "candidate_scope": "New mappings with available per-key capacity, individually reviewed for veterinary-medical relevance and translation precision.",
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
    manifest = build(prefilter, candidates, reviewed, inputs, base_manifest)
    print(json.dumps(manifest["counts"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
