"""Build batch 25: precise NAER translations for existing headwords.

This tranche only considers the 591 NAER pairs whose English headword already
exists in the keyboard baseline. Manual review is limited to pairs that also
match a MeSH medical term and an exact ECDICT noun gloss.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
SOURCE_DIR = DATA / "sources/naer"
SOURCE_CSV = SOURCE_DIR / "medical-academic-terms-2026-06-24.csv"
SOURCE_SHA256 = "5dfdea2f57d5cb9826006265f73d37d73dadc8dbc205bf317c9ddd09ec859537"

PREFILTER = DATA / "batches/25-naer-medical-existing-headwords-prefilter.tsv"
CANDIDATES = DATA / "batches/25-naer-medical-existing-headwords-candidates.tsv"
REVIEWED = DATA / "batches/25-naer-medical-existing-headwords-reviewed.tsv"
EXPANSION = DATA / "naer-medical-expansion-2.tsv"
TAGS = DATA / "naer-medical-tags-2.tsv"
MANIFEST = DATA / "naer-medical-manifest-2.json"

SOURCE = "NAER Medical Academic Terms OGDL v1.0"
MEDICAL_BIT = 1 << 8
BASE_MANIFEST = DATA / "naer-medical-manifest.json"
BASE_PREFILTER = DATA / "batches/24-naer-medical-prefilter.tsv"
BASE_EXPANSION = DATA / "naer-medical-expansion.tsv"
BASE_TAGS = DATA / "naer-medical-tags.tsv"
MESH_ARCHIVE = DATA / "sources/mesh/desc2026.zip"
MESH_SHA256 = "bb73dfdfe78cbfcd692ef399bb6df24750327ff62c4f53574826c56ba3d6a3f3"

PREFILTER_FIELDS = (
    "english", "chinese", "source_chinese", "source_records", "source_url_field",
    "pinyin", "pinyin_frequency", "ipa_sources", "noun_evidence",
    "already_mapped_after_batch_24", "spare_capacity_after_batch_24",
    "mesh_term_ids", "mesh_preferred_terms", "mesh_tree_numbers",
    "ecdict_exact_noun_glosses", "review_scope",
)
CANDIDATE_FIELDS = tuple(field for field in PREFILTER_FIELDS if field != "review_scope")
REVIEW_FIELDS = CANDIDATE_FIELDS + ("decision", "review_note")

ACCEPTED = {
    ("吸收", "absorption"): "Absorption is a recognized physiological and biomedical process; 吸收 is the exact ECDICT noun gloss.",
    ("焦虑", "anxiety"): "焦虑 is the direct clinical/psychological term and an exact local noun gloss.",
    ("注意", "attention"): "注意 is the direct cognitive/clinical term; MeSH includes Attention as a psychological concept.",
    ("失明", "blindness"): "失明 is exact for loss of vision.",
    ("呼吸", "breathing"): "呼吸 is exact; MeSH identifies the respiratory concept as Respiration.",
    ("阉割", "castration"): "阉割 is the direct medical procedure term.",
    ("耳垢", "cerumen"): "耳垢 is exact; cerumen is the anatomical/clinical term for earwax.",
    ("感冒", "cold"): "感冒 is an exact common medical noun sense of cold; the source is a medical glossary and ECDICT confirms the gloss.",
    ("死亡", "death"): "死亡 is exact in a clinical and public-health context.",
    ("脱水", "dehydration"): "脱水 is exact.",
    ("镊子", "forceps"): "镊子 is the direct instrument term; MeSH places forceps under surgical instruments.",
    ("生长", "growth"): "生长 is the biological growth sense and is supported by the MeSH Growth term.",
    ("健康", "health"): "健康 is the direct health-state term; the alternative source gloss 卫生 is deferred as less precise.",
    ("出血", "hemorrhage"): "出血 is the exact clinical term.",
    ("冬眠", "hibernation"): "冬眠 is exact in physiology.",
    ("门牙", "incisor"): "门牙 is a direct common anatomical name for an incisor.",
    ("运动", "movement"): "运动 is the direct physiological movement sense; MeSH includes Movement.",
    ("突变", "mutation"): "突变 is the established genetics/biomedical term.",
    ("指甲", "nail"): "指甲 is the exact anatomical nail sense; MeSH includes Nails.",
    ("看护", "nursing"): "看护 is the direct care sense; the MeSH Nursing concept covers professional nursing practice.",
    ("杀虫剂", "pesticide"): "杀虫剂 is exact and relevant to toxicology.",
    ("石炭酸", "phenol"): "石炭酸 is an established synonym for phenol.",
    ("怀孕", "pregnancy"): "怀孕 is an exact, commonly used Chinese translation of pregnancy.",
    ("再生", "regeneration"): "再生 is the direct biological/tissue process sense.",
    ("复发", "relapse"): "复发 is exact for recurrence of a disease or symptoms.",
    ("破裂", "rupture"): "破裂 is the direct anatomical/pathological sense.",
    ("硬化", "sclerosis"): "硬化 is the direct pathological process term; MeSH includes Sclerosis.",
    ("抽烟", "smoking"): "抽烟 is the direct behavioral/clinical term.",
    ("跗骨", "tarsus"): "跗骨 is the anatomical foot-bone term.",
    ("治疗", "therapy"): "治疗 is exact; MeSH includes Therapeutics as a treatment concept.",
    ("组织", "tissue"): "组织 is exact in histology and anatomy; MeSH includes Tissues.",
    ("移植", "transplantation"): "移植 is the established clinical procedure term.",
    ("治疗", "treatment"): "治疗 is exact in clinical care; MeSH maps treatment concepts under Therapeutics.",
    ("内脏", "viscera"): "内脏 is exact for the internal organs.",
    ("视力", "vision"): "视力 is the exact ocular sense; the MeSH preferred term is Vision, Ocular.",
    ("呕吐", "vomiting"): "呕吐 is exact.",
    ("创伤", "wound"): "创伤 is an accepted concise clinical injury sense and an exact ECDICT noun gloss.",
}

REJECTED = {
    ("冻疮", "frostbite"): "冻疮 usually means chilblains/pernio; frostbite is 冻伤, so this source gloss is misleading.",
    ("分离", "separation"): "The matching MeSH English entry is Divorce, not a medical separation concept; the source pair lacks clear medical scope.",
    ("肿块", "tumor"): "肿块 is a mass/lump; tumor is more precisely 肿瘤, so this short mapping is misleading.",
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


def load_inputs() -> tuple[dict, dict, list[dict[str, str]], dict]:
    if sha(SOURCE_CSV.read_bytes()) != SOURCE_SHA256:
        raise SystemExit("Pinned NAER medical terminology CSV SHA-256 mismatch")
    base_manifest = json.loads(BASE_MANIFEST.read_text(encoding="utf-8"))
    if sha(BASE_PREFILTER.read_bytes()) != base_manifest["outputs"][BASE_PREFILTER.name]:
        raise SystemExit("NAER batch 24 prefilter hash mismatch")
    if sha(BASE_EXPANSION.read_bytes()) != base_manifest["outputs"][BASE_EXPANSION.name]:
        raise SystemExit("NAER batch 24 expansion hash mismatch")
    if sha(BASE_TAGS.read_bytes()) != base_manifest["outputs"][BASE_TAGS.name]:
        raise SystemExit("NAER batch 24 tag hash mismatch")
    if sha(MESH_ARCHIVE.read_bytes()) != MESH_SHA256:
        raise SystemExit("NLM MeSH 2026 archive SHA-256 mismatch")

    sys.path.insert(0, str(ROOT / "scripts"))
    import build_naer_medical_batch as naer_batch
    import build_mesh_medical_batch as mesh_batch

    inputs = naer_batch.load_inputs()
    for line in BASE_EXPANSION.read_text(encoding="utf-8").splitlines():
        chinese, english, _pos, _source = line.split("\t")
        pair = (chinese, english)
        if pair not in inputs["pairs"]:
            inputs["pairs"].add(pair)
            inputs["extras"][chinese] = inputs["extras"].get(chinese, 0) + 1
        inputs["words"].add(english.casefold())
    for line in BASE_TAGS.read_text(encoding="utf-8").splitlines():
        english, _mask, _source = line.split("\t")
        inputs["existing_medical_tags"].add(english.casefold())
    descriptors, term_index = mesh_batch.read_mesh()
    descriptor_by_id = {row["mesh_id"]: row for row in descriptors}
    return inputs, term_index, descriptor_by_id, base_manifest


def discover(inputs: dict, term_index: dict, descriptors: dict[str, dict[str, str]], base_manifest: dict):
    from opencc import OpenCC

    converter = OpenCC("t2s")
    with BASE_PREFILTER.open(encoding="utf-8", newline="") as stream:
        batch24_prefilter = list(csv.DictReader(stream, delimiter="\t"))
    rows = []
    for original in batch24_prefilter:
        if original["existing_headword"] != "true":
            continue
        english = original["english"]
        chinese = original["chinese"]
        glosses = sorted({
            converter.convert(gloss).strip()
            for gloss, pos in inputs["ecdict"].get(english, ())
            if pos == "n."
        })
        exact_glosses = [gloss for gloss in glosses if gloss == chinese]
        mesh_evidence = term_index.get(english, {"ids": set(), "preferred": set(), "trees": set()})
        mesh_ids = sorted(mesh_evidence["ids"])
        if mesh_ids:
            preferred_terms = sorted({descriptors[mid]["english"] for mid in mesh_ids if mid in descriptors})
            tree_numbers = sorted({tree for mid in mesh_ids if mid in descriptors
                                   for tree in descriptors[mid]["tree_numbers"].split(",") if tree})
        else:
            preferred_terms, tree_numbers = [], []
        already_mapped = (chinese, english) in inputs["pairs"]
        spare_capacity = inputs["extras"].get(chinese, 0) < 8
        row = {
            "english": english,
            "chinese": chinese,
            "source_chinese": original["source_chinese"],
            "source_records": original["source_records"],
            "source_url_field": original["source_url_field"],
            "pinyin": original["pinyin"],
            "pinyin_frequency": original["pinyin_frequency"],
            "ipa_sources": original["ipa_sources"],
            "noun_evidence": original["noun_evidence"],
            "already_mapped_after_batch_24": str(already_mapped).lower(),
            "spare_capacity_after_batch_24": str(spare_capacity).lower(),
            "mesh_term_ids": ",".join(mesh_ids),
            "mesh_preferred_terms": " | ".join(preferred_terms),
            "mesh_tree_numbers": ",".join(tree_numbers),
            "ecdict_exact_noun_glosses": " | ".join(exact_glosses),
            "review_scope": "exact_ECDICT_noun_gloss_and_MeSH_term" if exact_glosses and mesh_ids and spare_capacity and not already_mapped else "not_in_intersection",
        }
        rows.append(row)
    rows.sort(key=lambda row: (row["english"], row["chinese"], row["source_records"]))
    prefilter = rows
    candidates = [
        {field: row[field] for field in CANDIDATE_FIELDS}
        for row in rows
        if row["ecdict_exact_noun_glosses"]
        and row["mesh_term_ids"]
        and row["spare_capacity_after_batch_24"] == "true"
        and row["already_mapped_after_batch_24"] == "false"
    ]
    return prefilter, candidates


def review(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    reviewed = []
    seen = set()
    for row in candidates:
        key = (row["chinese"], row["english"])
        if key in seen:
            raise SystemExit(f"Duplicate NAER/MeSH/ECDICT candidate: {key}")
        seen.add(key)
        if key in ACCEPTED:
            decision, note = "accept", ACCEPTED[key]
        elif key in REJECTED:
            decision, note = "reject", REJECTED[key]
        else:
            decision = "defer"
            note = "雖有官方英中對照、ECDICT 完整名詞義和 MeSH 關聯，但孤立中文詞面不夠精確或英文詞面有多義；暫不加入。"
        reviewed.append({field: row[field] for field in CANDIDATE_FIELDS} | {
            "decision": decision,
            "review_note": note,
        })
    missing = (set(ACCEPTED) | set(REJECTED)) - seen
    if missing:
        raise SystemExit(f"Curated NAER batch 25 decisions absent from intersection: {sorted(missing)}")
    return reviewed


def build(prefilter: list[dict[str, str]], candidates: list[dict[str, str]], reviewed: list[dict[str, str]], inputs: dict,
          base_manifest: dict) -> dict:
    accepted = [row for row in reviewed if row["decision"] == "accept"]
    rejected = [row for row in reviewed if row["decision"] == "reject"]
    deferred = [row for row in reviewed if row["decision"] == "defer"]
    accepted_per_key: Counter[str] = Counter(row["chinese"] for row in accepted)
    over_capacity = {
        chinese: inputs["extras"].get(chinese, 0) + count
        for chinese, count in accepted_per_key.items()
        if inputs["extras"].get(chinese, 0) + count > 8
    }
    if over_capacity:
        raise SystemExit(f"Accepted NAER batch 25 rows exceed the per-key limit: {over_capacity}")
    expansion_rows = [{
        "chinese": row["chinese"], "english": row["english"], "pos": "n.", "source": SOURCE,
    } for row in accepted]
    expansion_rows.sort(key=lambda row: (row["chinese"], row["english"]))
    accepted_words = {row["english"] for row in accepted}
    new_headwords = sorted(word for word in accepted_words if word not in inputs["words"])
    if new_headwords:
        raise SystemExit(f"Batch 25 unexpectedly contains new English headwords: {new_headwords}")
    new_tag_words = sorted(accepted_words - inputs["existing_medical_tags"])
    tag_rows = [{"english": word, "mask": str(MEDICAL_BIT), "source": SOURCE} for word in new_tag_words]

    prefilter_bytes = write_tsv(PREFILTER, PREFILTER_FIELDS, prefilter)
    candidate_bytes = write_tsv(CANDIDATES, CANDIDATE_FIELDS, candidates)
    reviewed_bytes = write_tsv(REVIEWED, REVIEW_FIELDS, reviewed)
    expansion_bytes = write_tsv(EXPANSION, ("chinese", "english", "pos", "source"), expansion_rows, header=False)
    tag_bytes = write_tsv(TAGS, ("english", "mask", "source"), tag_rows, header=False)
    source_hashes = {
        "medical-academic-terms-2026-06-24.csv": SOURCE_SHA256,
        **base_manifest["source_hashes"],
        BASE_PREFILTER.name: base_manifest["outputs"][BASE_PREFILTER.name],
        BASE_EXPANSION.name: base_manifest["outputs"][BASE_EXPANSION.name],
        BASE_TAGS.name: base_manifest["outputs"][BASE_TAGS.name],
        MESH_ARCHIVE.name: MESH_SHA256,
    }
    manifest = {
        "batch": "25-naer-medical-existing-headwords",
        "source": {
            "title": "National Academy for Educational Research - Medical Academic Terms",
            "dataset_url": "https://taic.moda.gov.tw/datasets/4ca6b322-b160-41dd-a16a-02249f540bf8",
            "license": "Open Government Data License v1.0",
            "license_url": "https://data.gov.tw/license",
            "source_sha256": SOURCE_SHA256,
            "mesh_version": "NLM MeSH 2026",
            "mesh_archive_sha256": MESH_SHA256,
        },
        "filters": {
            "base_candidates": "NAER batch 24 prefilter rows marked existing_headword=true",
            "manual_review": "exact ECDICT noun gloss after OpenCC t2s AND English headword is a MeSH term",
            "candidate_capacity_limit": 8,
        },
        "counts": {
            "existing_headword_pairs_in_batch24_prefilter": len(prefilter),
            "mesh_and_exact_ecdict_intersection": len(candidates),
            "accepted_mappings": len(accepted),
            "rejected_candidates": len(rejected),
            "deferred_candidates": len(deferred),
            "accepted_new_english_headwords": len(new_headwords),
            "new_medical_tag_memberships": len(new_tag_words),
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


def main() -> None:
    inputs, term_index, descriptors, base_manifest = load_inputs()
    prefilter, candidates = discover(inputs, term_index, descriptors, base_manifest)
    reviewed = review(candidates)
    manifest = build(prefilter, candidates, reviewed, inputs, base_manifest)
    print(json.dumps(manifest["counts"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
