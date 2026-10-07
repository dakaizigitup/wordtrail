"""Build reviewed batch 24 from the pinned NAER medical terminology dataset.

The full government-open bilingual source is retained for attribution and
reproducibility. Runtime output contains only individually accepted short
translations whose English headword has local IPA and noun evidence, whose
Chinese key is reachable, and which still fits the per-key expansion limit.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
SOURCE_DIR = DATA / "sources/naer"
SOURCE_CSV = SOURCE_DIR / "medical-academic-terms-2026-06-24.csv"
SOURCE_METADATA = SOURCE_DIR / "dataset.json"
SOURCE_SHA256 = "5dfdea2f57d5cb9826006265f73d37d73dadc8dbc205bf317c9ddd09ec859537"
SOURCE_METADATA_SHA256 = "a10f3b993bc6e098ee19a3f693b668f11f3a67bf1518ab6fe518490a67c886ff"

PREFILTER = DATA / "batches/24-naer-medical-prefilter.tsv"
CANDIDATES = DATA / "batches/24-naer-medical-candidates.tsv"
REVIEWED = DATA / "batches/24-naer-medical-reviewed.tsv"
EXPANSION = DATA / "naer-medical-expansion.tsv"
TAGS = DATA / "naer-medical-tags.tsv"
MANIFEST = DATA / "naer-medical-manifest.json"

SOURCE = "NAER Medical Academic Terms OGDL v1.0"
MEDICAL_BIT = 1 << 8
WORD = re.compile(r"[a-z][a-z'-]*\Z")
VARIANT_SEPARATOR = re.compile(r"[；;、，,/／|]+")

PREFILTER_FIELDS = (
    "english", "chinese", "source_chinese", "source_records", "source_url_field",
    "pinyin", "pinyin_frequency", "ipa_sources", "noun_evidence",
    "already_mapped", "existing_headword", "spare_capacity", "review_scope",
)
CANDIDATE_FIELDS = tuple(field for field in PREFILTER_FIELDS if field != "review_scope")
REVIEW_FIELDS = CANDIDATE_FIELDS + ("decision", "review_note")

# Only direct, sufficiently specific medical/bioscience senses are shipped.
# The government glossary establishes the bilingual pair; review notes explain
# why the short isolated form remains useful in this keyboard's candidate UI.
ACCEPTED = {
    ("异常", "abnormalities"): "The source's plural headword maps directly to 异常; this is a common clinical descriptor.",
    ("活化", "activation"): "活化 is the direct chemistry/biomedical process sense.",
    ("肾上腺素", "adrenalin"): "肾上腺素 is the established hormone/drug name; adrenalin is a recognized spelling variant.",
    ("吻合", "anastomosis"): "吻合 is the established anatomical and surgical term.",
    ("动脉瘤", "aneurism"): "动脉瘤 is exact; aneurism is a recognized variant spelling of aneurysm.",
    ("测定", "assay"): "测定 is the direct analytical/clinical assay sense; less-specific source alternatives are deferred.",
    ("出血", "bleeding"): "出血 is exact in a clinical symptom/injury context.",
    ("钙化", "calcification"): "钙化 is the established pathological and tissue-change term.",
    ("辣椒", "capsicum"): "辣椒 is the standard Chinese name for Capsicum; retained as a medicinal/botanical substance term.",
    ("肉桂", "cassia"): "肉桂 is the direct name used for cassia cinnamon, a medicinal botanical substance.",
    ("分娩", "childbirth"): "分娩 is the precise clinical term; the broader source alternative 生产 is deferred.",
    ("挫伤", "contusion"): "挫伤 is the established clinical injury term.",
    ("皮肤", "cutis"): "Cutis is the anatomical term for skin; 皮肤 is exact.",
    ("缺失", "deletion"): "缺失 is the direct genetics/biomedical sense of deletion.",
    ("变形", "deformations"): "变形 is a direct morphology/pathology sense; broader context-specific entries remain deferred.",
    ("葡萄糖", "dextrose"): "葡萄糖 is exact; dextrose is a common name for D-glucose.",
    ("扩张", "dilatation"): "扩张 is the established anatomical/clinical process term.",
    ("排泄", "excretion"): "排泄 is the physiological process term.",
    ("脱落", "exfoliation"): "脱落 is the direct epithelial/skin shedding sense.",
    ("昏厥", "fainting"): "昏厥 is the clinical synonym for fainting.",
    ("妊娠", "gestation"): "妊娠 is the formal medical term; the colloquial source alternative 怀孕 is deferred.",
    ("淋病", "gonorrhoea"): "淋病 is exact; this is the British spelling.",
    ("出血", "haemorrhage"): "出血 is exact; this is the British spelling of hemorrhage.",
    ("荨麻疹", "hives"): "荨麻疹 is the direct clinical term.",
    ("杂交", "hybridization"): "杂交 is the direct genetics/biomedical sense.",
    ("黄疸", "icterus"): "黄疸 is the established clinical term.",
    ("植入", "implantation"): "植入 is the direct procedure/embryology sense; 移植 would imply transplantation and is deferred.",
    ("抑制剂", "inhibitors"): "抑制剂 is the established pharmacology/biochemistry term.",
    ("照射", "irradiation"): "照射 is the direct radiological/biomedical process sense.",
    ("白血球", "leukocyte"): "白血球 is an established Chinese synonym for 白细胞 and directly names the cell type.",
    ("梅毒", "lues"): "梅毒 is exact; lues is a historical medical synonym, retained with the medical tag.",
    ("不适", "malaise"): "不适 is the direct clinical symptom sense.",
    ("畸形", "malformation"): "畸形 is the established developmental/pathology term.",
    ("黏膜", "mucosa"): "黏膜 is exact.",
    ("肿瘤", "neoplasm"): "肿瘤 is the established clinical term.",
    ("腮腺", "parotid"): "腮腺 is the anatomical gland name used as a medical noun/modifier.",
    ("穿孔", "perforation"): "穿孔 is the direct anatomical/pathological term.",
    ("百日咳", "pertussis"): "百日咳 is exact.",
    ("噬菌体", "phage"): "噬菌体 is the standard microbiology term; phage is its common short form.",
    ("阴茎", "phallus"): "阴茎 is the direct anatomical sense.",
    ("耳廓", "pinna"): "耳廓 is the exact anatomical term.",
    ("搏动", "pulsation"): "搏动 is the direct physiological/clinical sense.",
    ("精神病", "psychosis"): "精神病 is the concise clinical term for psychosis.",
    ("发热", "pyrexia"): "发热 is the established clinical term; pyrexia is a medical synonym for fever.",
    ("逆流", "reflux"): "逆流 is the direct backward-flow sense; the source's more general alternative is deferred.",
    ("复位", "reposition"): "复位 is the direct clinical/surgical procedure sense.",
    ("分节", "segmentation"): "分节 is the direct embryological/anatomical process sense.",
    ("猩红热", "scarlatina"): "猩红热 is exact; scarlatina is a recognized historical synonym.",
    ("狭窄", "stenosis"): "狭窄 is the established pathological/anatomical term.",
    ("基质", "stroma"): "基质 is the accepted histological tissue-support term.",
    ("窒息", "suffocation"): "窒息 is exact in the clinical/physiological sense.",
    ("输血", "transfusion"): "输血 is the direct clinical procedure sense.",
    ("溃疡", "ulceration"): "溃疡 is the direct pathological condition/process sense.",
    ("水痘", "varicella"): "水痘 is exact.",
    ("天花", "variola"): "天花 is exact; variola is the disease name.",
    ("静脉", "vena"): "静脉 is the exact anatomical term; vena is the Latin-derived medical headword.",
    ("疣", "verruca"): "疣 is the exact medical term.",
}

REJECTED = {
    ("剥离", "ablation"): "In this medical context ablation is usually 消融/切除; 剥离 is misleading.",
    ("生长", "accretions"): "Accretions are accumulated deposits or growths, not the general process 生长.",
    ("茴香", "anise"): "茴香 usually names fennel and is not a reliable isolated equivalent for anise.",
    ("甲", "concha"): "甲 is not a sufficiently explicit translation of the anatomical concha.",
    ("紫草", "comfrey"): "Comfrey is not 紫草; the source pair is a botanical false match.",
    ("真皮", "derma"): "Derma means skin generally, not specifically 真皮.",
    ("鼠李", "cascara"): "Cascara refers to a particular medicinal bark; 鼠李 alone is too broad to ship without a specific species gloss.",
    ("氧化", "oxygenation"): "Oxygenation is not oxidation; this is a misleading false-friend mapping.",
    ("肾病", "nephrosis"): "肾病 is broader than nephrosis and loses the specific pathological concept.",
    ("栓塞", "thrombosis"): "血栓形成/血栓症 is thrombosis; 栓塞 is embolism, a different concept.",
    ("独眼", "cyclops"): "独眼 is not a reliable clinical gloss for the specific congenital condition.",
    ("尖", "cusp"): "尖 is not a reliable isolated equivalent for the anatomical/structural cusp sense.",
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


def load_inputs() -> dict:
    if sha(SOURCE_CSV.read_bytes()) != SOURCE_SHA256:
        raise SystemExit("Pinned NAER medical terminology CSV SHA-256 mismatch")
    if sha(SOURCE_METADATA.read_bytes()) != SOURCE_METADATA_SHA256:
        raise SystemExit("Pinned NAER dataset metadata SHA-256 mismatch")
    metadata = json.loads(SOURCE_METADATA.read_text(encoding="utf-8"))
    if (metadata.get("dataset_id") != "4ca6b322-b160-41dd-a16a-02249f540bf8"
            or metadata.get("snapshot_sha256") != SOURCE_SHA256):
        raise SystemExit("Unexpected NAER dataset metadata")

    sys.path.insert(0, str(ROOT / "scripts"))
    import build_mesh_medical_batch as mesh_batch

    inputs = mesh_batch.load_inputs()
    prior_expansions = (
        "mesh-medical-expansion.tsv",
        "wikidata-medical-expansion.tsv",
        "wikidata-medical-expansion-2.tsv",
    )
    prior_tags = (
        "mesh-medical-tags.tsv",
        "wikidata-medical-tags.tsv",
        "wikidata-medical-tags-2.tsv",
    )
    for filename in prior_expansions:
        for line in (DATA / filename).read_text(encoding="utf-8").splitlines():
            chinese, english, _pos, _source = line.split("\t")
            pair = (chinese, english)
            if pair not in inputs["pairs"]:
                inputs["pairs"].add(pair)
                inputs["extras"][chinese] = inputs["extras"].get(chinese, 0) + 1
            inputs["words"].add(english.casefold())
    for filename in prior_tags:
        for line in (DATA / filename).read_text(encoding="utf-8").splitlines():
            english, _mask, _source = line.split("\t")
            inputs["existing_medical_tags"].add(english.casefold())
    inputs["naer_input_hashes"] = {
        filename: sha((DATA / filename).read_bytes())
        for filename in (*prior_expansions, *prior_tags)
    }
    return inputs


def discover(inputs: dict) -> tuple[list[dict[str, str]], list[dict[str, str]], int]:
    from opencc import OpenCC

    converter = OpenCC("t2s")
    grouped: dict[tuple[str, str], dict] = {}
    ipa_words = inputs["uk"] | inputs["us"]
    noun_evidence = {
        word for word, senses in inputs["ecdict"].items()
        if any(pos == "n." for _gloss, pos in senses)
    }
    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        expected = {"序號", "英文名稱", "中文名稱", "來源網站"}
        if set(reader.fieldnames or ()) != expected:
            raise SystemExit(f"Unexpected NAER CSV columns: {reader.fieldnames}")
        source_records = 0
        for row in reader:
            source_records += 1
            english = row["英文名稱"].strip().casefold()
            if not WORD.fullmatch(english) or english not in ipa_words or english not in noun_evidence:
                continue
            variants = sorted({
                converter.convert(value.strip()).strip()
                for value in VARIANT_SEPARATOR.split(row["中文名稱"])
                if value.strip()
            })
            for chinese in variants:
                if chinese not in inputs["pinyin"]:
                    continue
                if inputs["extras"].get(chinese, 0) >= 8:
                    continue
                if (chinese, english) in inputs["pairs"]:
                    continue
                key = (chinese, english)
                entry = grouped.setdefault(key, {"records": set(), "source_chinese": set(), "source_urls": set()})
                entry["records"].add(row["序號"].strip())
                entry["source_chinese"].add(row["中文名稱"].strip())
                entry["source_urls"].add(row["來源網站"].strip())

    prefilter = []
    for (chinese, english), evidence in grouped.items():
        pinyin, frequency = inputs["pinyin"][chinese]
        prefilter.append({
            "english": english,
            "chinese": chinese,
            "source_chinese": " | ".join(sorted(evidence["source_chinese"])),
            "source_records": ",".join(sorted(evidence["records"], key=lambda value: int(value))),
            "source_url_field": " | ".join(sorted(evidence["source_urls"])),
            "pinyin": pinyin,
            "pinyin_frequency": str(frequency),
            "ipa_sources": ",".join(name for name, words in (("UK", inputs["uk"]), ("US", inputs["us"])) if english in words),
            "noun_evidence": "ECDICT n.",
            "already_mapped": "false",
            "existing_headword": str(english in inputs["words"]).lower(),
            "spare_capacity": str(inputs["extras"].get(chinese, 0) < 8).lower(),
            "review_scope": "new_headword" if english not in inputs["words"] else "existing_headword_pair",
        })
    prefilter.sort(key=lambda row: (row["english"], row["chinese"], row["source_records"]))
    candidates = [
        {field: row[field] for field in CANDIDATE_FIELDS}
        for row in prefilter if row["existing_headword"] == "false"
    ]
    return prefilter, candidates, source_records


def review(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    reviewed = []
    seen = set()
    for row in candidates:
        key = (row["chinese"], row["english"])
        if key in seen:
            raise SystemExit(f"Duplicate NAER candidate: {key}")
        seen.add(key)
        if key in ACCEPTED:
            decision, note = "accept", ACCEPTED[key]
        elif key in REJECTED:
            decision, note = "reject", REJECTED[key]
        else:
            decision = "defer"
            note = "官方英中对照可核验，但独立词面过宽、术语范围不清或更精确译法尚需来源交叉确认；暂不进入运行词库。"
        reviewed.append({field: row[field] for field in CANDIDATE_FIELDS} | {
            "decision": decision,
            "review_note": note,
        })
    missing = (set(ACCEPTED) | set(REJECTED)) - seen
    if missing:
        raise SystemExit(f"Curated NAER decisions are absent from eligible new-headword candidates: {sorted(missing)}")
    return reviewed


def build(prefilter: list[dict[str, str]], candidates: list[dict[str, str]], reviewed: list[dict[str, str]], inputs: dict,
          source_records: int) -> dict:
    accepted = [row for row in reviewed if row["decision"] == "accept"]
    rejected = [row for row in reviewed if row["decision"] == "reject"]
    deferred = [row for row in reviewed if row["decision"] == "defer"]
    accepted_per_key: dict[str, int] = defaultdict(int)
    for row in accepted:
        accepted_per_key[row["chinese"]] += 1
    over_capacity = {
        chinese: inputs["extras"].get(chinese, 0) + count
        for chinese, count in accepted_per_key.items()
        if inputs["extras"].get(chinese, 0) + count > 8
    }
    if over_capacity:
        raise SystemExit(f"Accepted NAER rows exceed the per-key expansion limit: {over_capacity}")
    expansion_rows = [{
        "chinese": row["chinese"], "english": row["english"], "pos": "n.", "source": SOURCE,
    } for row in accepted]
    expansion_rows.sort(key=lambda row: (row["chinese"], row["english"]))
    accepted_words = {row["english"] for row in accepted}
    new_tag_words = sorted(accepted_words - inputs["existing_medical_tags"])
    tag_rows = [{"english": word, "mask": str(MEDICAL_BIT), "source": SOURCE} for word in new_tag_words]

    pfilter_bytes = write_tsv(PREFILTER, PREFILTER_FIELDS, prefilter)
    candidate_bytes = write_tsv(CANDIDATES, CANDIDATE_FIELDS, candidates)
    reviewed_bytes = write_tsv(REVIEWED, REVIEW_FIELDS, reviewed)
    expansion_bytes = write_tsv(EXPANSION, ("chinese", "english", "pos", "source"), expansion_rows, header=False)
    tag_bytes = write_tsv(TAGS, ("english", "mask", "source"), tag_rows, header=False)

    source_hashes = {
        SOURCE_CSV.name: SOURCE_SHA256,
        SOURCE_METADATA.name: sha(SOURCE_METADATA.read_bytes()),
        **inputs["hashes"],
        **inputs["naer_input_hashes"],
    }
    manifest = {
        "batch": "24-naer-medical-academic-terms",
        "source": {
            "dataset_id": "4ca6b322-b160-41dd-a16a-02249f540bf8",
            "resource_id": "7bf30890-e4c4-4e81-9a98-b1d931a20894",
            "title": "National Academy for Educational Research - Medical Academic Terms",
            "provider": "National Academy for Educational Research",
            "published_at": "2026-06-24",
            "license": "Open Government Data License v1.0",
            "url": "https://taic.moda.gov.tw/datasets/4ca6b322-b160-41dd-a16a-02249f540bf8",
            "license_url": "https://data.gov.tw/license",
            "sha256": SOURCE_SHA256,
            "bytes": SOURCE_CSV.stat().st_size,
            "records": source_records,
            "note": "The source CSV's per-row 來源網站 field is the literal [url] placeholder; no independent row-level source URL is claimed.",
        },
        "filters": {
            "single_token_english": True,
            "local_ipa_required": True,
            "ecdict_noun_required": True,
            "local_pinyin_required": True,
            "traditional_to_simplified": "OpenCC t2s",
            "existing_exact_pairs_excluded": True,
            "candidate_capacity_limit": 8,
            "manual_review_scope": "new English headwords only; other pairs retained in prefilter for future review",
        },
        "counts": {
            "source_records": source_records,
            "eligible_unique_new_pairs": len(prefilter),
            "eligible_existing_headword_pairs": sum(row["existing_headword"] == "true" for row in prefilter),
            "reviewed_new_headword_candidates": len(candidates),
            "reviewed_new_english_headwords": len({row["english"] for row in candidates}),
            "accepted_mappings": len(accepted),
            "rejected_candidates": len(rejected),
            "deferred_candidates": len(deferred),
            "accepted_new_english_headwords": len(accepted_words),
            "new_medical_tag_memberships": len(new_tag_words),
        },
        "source_hashes": source_hashes,
        "outputs": {
            PREFILTER.name: sha(pfilter_bytes),
            CANDIDATES.name: sha(candidate_bytes),
            REVIEWED.name: sha(reviewed_bytes),
            EXPANSION.name: sha(expansion_bytes),
            TAGS.name: sha(tag_bytes),
        },
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    inputs = load_inputs()
    prefilter, candidates, source_records = discover(inputs)
    reviewed = review(candidates)
    manifest = build(prefilter, candidates, reviewed, inputs, source_records)
    print(json.dumps(manifest["counts"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
