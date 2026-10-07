"""Build batch 23 from a frozen full MeSH/Wikidata CC0 label crosswalk.

The output includes only explicitly reviewed, exact MeSH-ID-linked labels that
have a local pinyin key, IPA, ECDICT noun evidence, and spare candidate capacity.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
SOURCE_DIR = DATA / "sources/wikidata"
LABELS = SOURCE_DIR / "mesh-label-query-full-20261007.json"
ENTITIES = SOURCE_DIR / "mesh-entity-revisions-full-20261007.json"
QUERY = SOURCE_DIR / "mesh-label-query-20261007.rq"
QUERY_SCOPE = SOURCE_DIR / "mesh-query-scope-20261007.txt"
LABELS_SHA256 = "49f1f8b6e0954fa5cca25a6d692a5c1ae6e62be8d642c12dfd6d3391fde3a497"
ENTITIES_SHA256 = "15d513a3db152c780c8df663e6adf78f6ee839cc7c815ca095c942fcb575a9f4"
QUERY_SHA256 = "0f4b7ab22e7cc7571788a63b9ccd86f99a299f4a6f0ee22c9005f04a7b50dada"
QUERY_SCOPE_SHA256 = "1888452af8bac6dcf1f311c7cf67824fc192d6b1baaa32712964a4a137850533"
MESH_ARCHIVE = DATA / "sources/mesh/desc2026.zip"
MESH_SHA256 = "bb73dfdfe78cbfcd692ef399bb6df24750327ff62c4f53574826c56ba3d6a3f3"

EXPANSION = DATA / "wikidata-medical-expansion-2.tsv"
TAGS = DATA / "wikidata-medical-tags-2.tsv"
MANIFEST = DATA / "wikidata-medical-manifest-2.json"
CANDIDATES = DATA / "batches/23-wikidata-medical-candidates.tsv"
PREFILTER = DATA / "batches/23-wikidata-medical-prefilter.tsv"
REVIEWED = DATA / "batches/23-wikidata-medical-reviewed.tsv"

SOURCE = "Wikidata CC0 + NLM MeSH 2026"
MEDICAL_BIT = 1 << 8
LANG_PRIORITY = ("zh-cn", "zh-hans", "zh-sg")
CANDIDATE_FIELDS = (
    "mesh_id", "mesh_english", "chinese", "wikidata_qid", "wikidata_english",
    "label_language", "wikidata_revision", "modified_utc", "tree_numbers",
    "pinyin", "pinyin_frequency", "ipa_sources", "pos",
)
REVIEW_FIELDS = CANDIDATE_FIELDS + ("decision", "review_note")
PREFILTER_FIELDS = CANDIDATE_FIELDS + ("already_in_baseline", "already_in_runtime")

# Keep this tranche useful for medicine, anatomy, physiology, and clinical
# practice. A direct crosswalk is necessary evidence, not by itself sufficient
# reason to accept a broad, dated, or misleading Chinese label.
ACCEPTED = {
    ("D000438", "醇"): "Alcohols are a chemical class within the MeSH substances tree; 醇 is the concise technical Chinese term.",
    ("D000468", "碱"): "Alkalies are basic chemical substances; 碱 is the standard concise chemistry term.",
    ("D001046", "春药"): "Aphrodisiacs are substances used to increase sexual desire; 春药 is the direct Chinese term.",
    ("D003815", "牙医"): "Dentists are dental health professionals; 牙医 is exact.",
    ("D007022", "低血压"): "Hypotension is abnormally low blood pressure; 低血压 is exact.",
    ("D007267", "注射"): "Injections are administration by injection; 注射 is exact.",
    ("D054368", "泻药"): "Laxatives are agents used to relieve constipation; 泻药 is exact.",
    ("D007989", "性冲动"): "Libido is sexual desire/drive; 性冲动 is an established concise equivalent.",
    ("D009558", "乳头"): "Nipples are the anatomical structures; 乳头 is exact.",
    ("D010575", "农药"): "Pesticides are agents used to control pests and are a toxicology topic; 农药 is exact.",
    ("D010919", "安慰剂"): "Placebos are inactive or sham interventions used as controls; 安慰剂 is exact.",
    ("D011208", "粉末"): "Powders are a recognized pharmaceutical preparation form under MeSH D26; 粉末 is exact in that dosage-form context.",
    ("D055656", "处方"): "A medical prescription is an order for treatment/medication; 处方 is exact.",
    ("D018805", "败血症"): "Sepsis is a life-threatening response to infection; 败血症 is the established Chinese medical term.",
    ("D013009", "梦游"): "Somnambulism is sleepwalking; 梦游 is exact.",
    ("D013594", "注射器"): "Syringes are devices for injection; 注射器 is exact.",
    ("D013607", "片剂"): "Tablets are solid pharmaceutical dosage forms; 片剂 is exact in this MeSH context.",
    ("D013812", "疗法"): "MeSH defines therapeutics as procedures for treatment or prevention of disease; 疗法 is a concise matching term.",
    ("D014836", "意志"): "Volition is the faculty/process of willing or choosing; 意志 is the exact psychological term.",
}
REJECTED = {
    ("D003250", "缠绕"): "缠绕 means winding/entangling, not the physiological constriction concept.",
    ("D004531", "蛋"): "The Wikidata item is specifically egg as food; the MeSH descriptor has broader scope.",
    ("D006733", "角"): "角 is highly ambiguous and does not distinguish anatomical horns from unrelated senses.",
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


def load_inputs() -> tuple[dict, dict[str, dict[str, str]], list[dict], dict[str, dict]]:
    if sha(LABELS.read_bytes()) != LABELS_SHA256:
        raise SystemExit("Full Wikidata MeSH label snapshot SHA-256 mismatch")
    if sha(ENTITIES.read_bytes()) != ENTITIES_SHA256:
        raise SystemExit("Full Wikidata entity revision snapshot SHA-256 mismatch")
    if sha(QUERY.read_bytes()) != QUERY_SHA256 or sha(QUERY_SCOPE.read_bytes()) != QUERY_SCOPE_SHA256:
        raise SystemExit("Pinned Wikidata MeSH query or ID scope SHA-256 mismatch")
    if sha(MESH_ARCHIVE.read_bytes()) != MESH_SHA256:
        raise SystemExit("NLM MeSH 2026 archive SHA-256 mismatch")

    sys.path.insert(0, str(ROOT / "scripts"))
    import build_mesh_medical_batch as mesh_batch

    inputs = mesh_batch.load_inputs()
    for filename in ("mesh-medical-expansion.tsv", "wikidata-medical-expansion.tsv"):
        for line in (DATA / filename).read_text(encoding="utf-8").splitlines():
            chinese, english, _pos, _source = line.split("\t")
            inputs["pairs"].add((chinese, english))
            inputs["extras"][chinese] = inputs["extras"].get(chinese, 0) + 1
    for filename in ("mesh-medical-tags.tsv", "wikidata-medical-tags.tsv"):
        for line in (DATA / filename).read_text(encoding="utf-8").splitlines():
            english, _mask, _source = line.split("\t")
            inputs["existing_medical_tags"].add(english.casefold())
    prior_expansions = ("mesh-medical-expansion.tsv", "wikidata-medical-expansion.tsv")
    inputs["runtime_existing_words"] = set(inputs["words"]) | {
        line.split("\t")[1].casefold()
        for filename in prior_expansions
        for line in (DATA / filename).read_text(encoding="utf-8").splitlines()
    }
    inputs["mesh_input_hashes"].update({
        filename: sha((DATA / filename).read_bytes())
        for filename in (*prior_expansions, "mesh-medical-tags.tsv", "wikidata-medical-tags.tsv")
    })

    descriptors, _ = mesh_batch.read_mesh()
    mesh_by_id = {row["mesh_id"]: row for row in descriptors}
    labels_data = json.loads(LABELS.read_text(encoding="utf-8"))
    entity_data = json.loads(ENTITIES.read_text(encoding="utf-8"))["entities"]
    query_ids = set(QUERY_SCOPE.read_text(encoding="utf-8").splitlines())
    observed_ids = {row.get("mesh", {}).get("value", "") for row in labels_data}
    if len(query_ids) != 1326 or not observed_ids <= query_ids:
        raise SystemExit("Wikidata label snapshot falls outside the pinned 1,326-ID MeSH scope")
    return inputs, mesh_by_id, labels_data, entity_data


def discover(inputs: dict, mesh_by_id: dict[str, dict[str, str]], labels_data: list[dict],
             entity_data: dict[str, dict], *, include_existing_headwords: bool = False) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in labels_data:
        mesh_id = row.get("mesh", {}).get("value", "")
        lang = row.get("zh", {}).get("xml:lang", "")
        if mesh_id in mesh_by_id and lang in LANG_PRIORITY and row.get("zh", {}).get("value"):
            grouped[(mesh_id, row["zh"]["value"])].append(row)

    ipa_words = inputs["uk"] | inputs["us"]
    candidates = []
    for (mesh_id, chinese), rows in grouped.items():
        descriptor = mesh_by_id[mesh_id]
        english = descriptor["english"].casefold()
        if (english in inputs["words"] and not include_existing_headwords) or english not in ipa_words:
            continue
        if chinese not in inputs["pinyin"]:
            continue
        if not any(pos == "n." for _gloss, pos in inputs["ecdict"].get(english, set())):
            continue
        if inputs["extras"].get(chinese, 0) >= 8 or (chinese, english) in inputs["pairs"]:
            continue

        source_rows = sorted(rows, key=lambda row: (
            LANG_PRIORITY.index(row["zh"]["xml:lang"]),
            row["item"]["value"],
            row.get("en", {}).get("value", ""),
        ))
        qids = {row["item"]["value"].rsplit("/", 1)[-1] for row in source_rows}
        if len(qids) != 1:
            raise SystemExit(f"Ambiguous Wikidata item mapping for {mesh_id}: {chinese}: {sorted(qids)}")
        qid = next(iter(qids))
        entity = entity_data.get(qid)
        if entity is None or mesh_id not in entity["mesh_ids"]:
            raise SystemExit(f"Wikidata entity lacks exact MeSH P486 assertion: {qid} / {mesh_id}")
        chosen = source_rows[0]
        lang = chosen["zh"]["xml:lang"]
        if entity["labels"].get(lang) != chinese:
            raise SystemExit(f"Pinned entity label differs from WDQS snapshot: {qid} / {lang}")
        pinyin, frequency = inputs["pinyin"][chinese]
        candidates.append({
            "mesh_id": mesh_id,
            "mesh_english": descriptor["english"],
            "chinese": chinese,
            "wikidata_qid": qid,
            "wikidata_english": chosen.get("en", {}).get("value", "") or entity["labels"].get("en", ""),
            "label_language": lang,
            "wikidata_revision": str(entity["lastrevid"]),
            "modified_utc": entity["modified"],
            "tree_numbers": descriptor["tree_numbers"],
            "pinyin": pinyin,
            "pinyin_frequency": str(frequency),
            "ipa_sources": ",".join(
                name for name, words in (("UK", inputs["uk"]), ("US", inputs["us"]))
                if english in words
            ),
            "pos": "n.",
        })
    candidates.sort(key=lambda row: (row["mesh_english"].casefold(), row["chinese"], row["wikidata_qid"]))
    return candidates


def review(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    reviewed = []
    seen = set()
    for row in candidates:
        key = (row["mesh_id"], row["chinese"])
        if key in seen:
            raise SystemExit(f"Duplicate Wikidata candidate: {key}")
        seen.add(key)
        if key in ACCEPTED:
            decision, note = "accept", ACCEPTED[key]
        elif key in REJECTED:
            decision, note = "reject", REJECTED[key]
        else:
            decision = "defer"
            note = "MeSH/Wikidata 编号关系可核验，但该译词不够精确、专业关联较弱或尚需语境复核；暂不进入运行词库。"
        reviewed.append({**row, "decision": decision, "review_note": note})
    missing = (set(ACCEPTED) | set(REJECTED)) - seen
    if missing:
        raise SystemExit(f"Curated decisions are absent from eligible candidates: {sorted(missing)}")
    return reviewed


def build(candidates: list[dict[str, str]], reviewed: list[dict[str, str]], inputs: dict,
          prefilter: list[dict[str, str]]) -> dict:
    prefilter_rows = [
        {
            **row,
            "already_in_baseline": str(row["mesh_english"].casefold() in inputs["words"]).lower(),
            "already_in_runtime": str(row["mesh_english"].casefold() in inputs["runtime_existing_words"]).lower(),
        }
        for row in prefilter
    ]
    prefilter_bytes = write_tsv(PREFILTER, PREFILTER_FIELDS, prefilter_rows)
    candidate_bytes = write_tsv(CANDIDATES, CANDIDATE_FIELDS, candidates)
    reviewed_bytes = write_tsv(REVIEWED, REVIEW_FIELDS, reviewed)
    accepted = [row for row in reviewed if row["decision"] == "accept"]
    expansion_rows = [{
        "chinese": row["chinese"], "english": row["mesh_english"].casefold(),
        "pos": "n.", "source": SOURCE,
    } for row in accepted]
    expansion_rows.sort(key=lambda row: (row["chinese"], row["english"]))
    accepted_words = {row["mesh_english"].casefold() for row in accepted}
    tag_words = sorted(accepted_words - inputs["existing_medical_tags"])
    tag_rows = [{"english": word, "mask": str(MEDICAL_BIT), "source": SOURCE} for word in tag_words]
    expansion_bytes = write_tsv(EXPANSION, ("chinese", "english", "pos", "source"), expansion_rows, header=False)
    tag_bytes = write_tsv(TAGS, ("english", "mask", "source"), tag_rows, header=False)

    source_hashes = {
        LABELS.name: sha(LABELS.read_bytes()),
        ENTITIES.name: sha(ENTITIES.read_bytes()),
        QUERY.name: sha(QUERY.read_bytes()),
        QUERY_SCOPE.name: sha(QUERY_SCOPE.read_bytes()),
        "NLM-MeSH-2026-desc.zip": MESH_SHA256,
    }
    entities = json.loads(ENTITIES.read_text(encoding="utf-8"))["entities"]
    manifest = {
        "batch": "23-wikidata-mesh-medical",
        "sources": [
            {"name": "Wikidata structured data", "license": "CC0 1.0", "url": "https://www.wikidata.org/wiki/Wikidata:Licensing"},
            {"name": "NLM Medical Subject Headings (MeSH), 2026", "terms": "Free use with NLM attribution and version identification", "url": "https://www.nlm.nih.gov/databases/download/terms_and_conditions_mesh.html"},
        ],
        "wikidata_snapshot": {
            "retrieved_at_utc": "2026-10-07",
            "query_endpoint": "https://query.wikidata.org/sparql",
            "mesh_descriptor_ids_in_query": 1326,
            "label_query_rows": len(json.loads(LABELS.read_text(encoding="utf-8"))),
            "entity_revision_records": len(entities),
            "query_languages": list(LANG_PRIORITY),
            "crosswalk_property": "P486 (MeSH Descriptor ID)",
        },
        "translation_method": "Chinese Wikidata labels are joined to the preferred MeSH 2026 English descriptor by exact P486 ID; each candidate entity revision independently records the same P486 ID and Chinese label.",
        "candidate_filter": "Existing pinyin key; local UK or US IPA; ECDICT noun POS evidence; spare per-key capacity; no duplicate pair; exact MeSH descriptor within the selected NLM tree scope.",
        "source_sha256": source_hashes,
        "runtime_input_sha256": inputs["mesh_input_hashes"],
        "candidates": len(candidates),
        "prefilter_candidates": len(prefilter_rows),
        "accepted_mappings": len(accepted),
        "accepted_new_english_headwords": len(accepted_words - inputs["runtime_existing_words"]),
        "rejected_candidates": sum(row["decision"] == "reject" for row in reviewed),
        "deferred_candidates": sum(row["decision"] == "defer" for row in reviewed),
        "new_medical_tag_memberships": len(tag_rows),
        "accepted_rows": [f"{row['chinese']} -> {row['english']} ({row['pos']})" for row in expansion_rows],
        "wikidata_entity_revisions": {row["wikidata_qid"]: row["wikidata_revision"] for row in accepted},
        "outputs": {
            EXPANSION.name: {"rows": len(expansion_rows), "sha256": sha(expansion_bytes)},
            TAGS.name: {"rows": len(tag_rows), "sha256": sha(tag_bytes)},
            CANDIDATES.relative_to(DATA).as_posix(): {"rows": len(candidates), "sha256": sha(candidate_bytes)},
            PREFILTER.relative_to(DATA).as_posix(): {"rows": len(prefilter_rows), "sha256": sha(prefilter_bytes)},
            REVIEWED.relative_to(DATA).as_posix(): {"rows": len(reviewed), "sha256": sha(reviewed_bytes)},
        },
        "runtime_note": "Only reviewed short mappings and compact medical tags are compiled into the runtime; snapshots and audit tables are not scanned while typing.",
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discover", action="store_true")
    args = parser.parse_args()
    inputs, mesh_by_id, labels_data, entity_data = load_inputs()
    prefilter = discover(inputs, mesh_by_id, labels_data, entity_data, include_existing_headwords=True)
    candidates = [row for row in prefilter if row["mesh_english"].casefold() not in inputs["words"]]
    if args.discover:
        print(json.dumps({
            "prefilter_candidates": len(prefilter),
            "existing_baseline_headwords": len(prefilter) - len(candidates),
            "review_candidates": len(candidates),
            "candidate_headwords": len({row['mesh_english'] for row in candidates}),
        }, ensure_ascii=False, indent=2))
        return
    manifest = build(candidates, review(candidates), inputs, prefilter)
    print(json.dumps({key: manifest[key] for key in ("candidates", "accepted_mappings", "accepted_new_english_headwords", "rejected_candidates", "deferred_candidates", "new_medical_tag_memberships")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
