"""Build a reviewed medical-vocabulary extension from Wikidata CC0 labels.

Wikidata labels are accepted only when the entity has the exact pinned NLM
MeSH descriptor ID, the Chinese label is an existing pinyin key, the English
headword has a local noun sense and IPA, and a reviewer explicitly accepts it.
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
LABELS = SOURCE_DIR / "mesh-label-query-20261007.json"
ENTITIES = SOURCE_DIR / "mesh-entity-revisions-20261007.json"
LABELS_SHA256 = "754cf2c43a6dc6b21f44b09c24f95bb8ad37d0857364d33e200614c83ff39569"
ENTITIES_SHA256 = "1c331dd24ca8cb862d614535998b716471eab9107aa32ed58c7d97c6757b3d01"
MESH_ARCHIVE = DATA / "sources/mesh/desc2026.zip"
MESH_SHA256 = "bb73dfdfe78cbfcd692ef399bb6df24750327ff62c4f53574826c56ba3d6a3f3"

EXPANSION = DATA / "wikidata-medical-expansion.tsv"
TAGS = DATA / "wikidata-medical-tags.tsv"
MANIFEST = DATA / "wikidata-medical-manifest.json"
CANDIDATES = DATA / "batches/22-wikidata-medical-candidates.tsv"
REVIEWED = DATA / "batches/22-wikidata-medical-reviewed.tsv"

SOURCE = "Wikidata CC0 + NLM MeSH 2026"
MEDICAL_BIT = 1 << 8
LANG_PRIORITY = ("zh-cn", "zh-hans", "zh-sg")
CANDIDATE_FIELDS = (
    "mesh_id", "mesh_english", "chinese", "wikidata_qid", "wikidata_english",
    "label_language", "wikidata_revision", "modified_utc", "tree_numbers",
    "pinyin", "pinyin_frequency", "ipa_sources", "pos",
)
REVIEW_FIELDS = CANDIDATE_FIELDS + ("decision", "review_note")

# Curated against the exact MeSH descriptor and Wikidata item label. Unlisted
# mechanically eligible rows remain explicitly deferred.
ACCEPTED = {
    ("D002196", "毛细血管"): "Wikidata Q103142 links this Chinese label to MeSH D002196 Capillaries; established anatomical term.",
    ("D004190", "灾害"): "Wikidata Q3839081 links the Chinese label to MeSH D004190 Disasters; exact concise translation.",
    ("D049248", "斩首"): "Wikidata Q204933 links the Chinese label to MeSH D049248 Decapitation; exact term in trauma/anatomy context.",
    ("D004242", "潜水"): "Wikidata Q179643 links the Chinese label to MeSH D004242 Diving; exact activity term.",
    ("D005107", "爆炸"): "Wikidata Q179057 links the Chinese label to MeSH D005107 Explosions; exact concise translation.",
    ("D005374", "过滤"): "Wikidata Q244772 links the Chinese label to MeSH D005374 Filtration; exact process term.",
    ("D055868", "洪灾"): "Wikidata Q8068 links the Chinese label to MeSH D055868 Floods; exact natural-hazard term.",
    ("D065928", "森林"): "Wikidata Q4421 links the Chinese label to MeSH D065928 Forests; exact environmental term.",
    ("D005740", "气体"): "Wikidata Q11432 links the Chinese label to MeSH D005740 Gases; exact chemical-science term.",
    ("D007088", "错觉"): "Wikidata Q182593 links the Chinese label to MeSH D007088 Illusions; exact psychological term.",
    ("D007239", "感染"): "Wikidata Q166231 links the Chinese label to MeSH D007239 Infections; exact clinical term.",
    ("D055876", "山崩"): "Wikidata Q167903 links the zh-sg simplified label to MeSH D055876 Landslides; exact natural-hazard synonym.",
    ("D007834", "激光器"): "Wikidata Q38867 links the Chinese label to MeSH D007834 Lasers; exact device term.",
    ("D016740", "经络"): "Wikidata Q1413962 links the Chinese label to MeSH D016740 Meridians; exact traditional-medicine term.",
    ("D008872", "微波"): "Wikidata Q127995 links the Chinese label to MeSH D008872 Microwaves; exact scientific term.",
    ("D009790", "职业"): "Wikidata Q12737077 links the Chinese label to MeSH D009790 Occupations; retained as an occupational-health topic.",
    ("D041361", "奶嘴"): "Wikidata Q152596 links the Chinese label to MeSH D041361 Pacifiers; exact device term.",
    ("D010969", "塑料"): "Wikidata Q11474 links the Chinese label to MeSH D010969 Plastics; exact materials term.",
    ("D058105", "聚合"): "Wikidata Q181898 links the Chinese label to MeSH D058105 Polymerization; exact process term.",
    ("D011108", "聚合物"): "Wikidata Q81163 links the Chinese label to MeSH D011108 Polymers; exact materials term.",
    ("D013638", "焦油"): "Wikidata Q186209 links the Chinese label to MeSH D013638 Tars; exact substance term.",
    ("D055869", "龙卷风"): "Wikidata Q8081 links the Chinese label to MeSH D055869 Tornadoes; exact natural-hazard term.",
    ("D014554", "排尿"): "Wikidata Q105726 links the Chinese label to MeSH D014554 Urination; exact clinical term.",
    ("D014860", "疣"): "Wikidata Q101971 links the Chinese label to MeSH D014860 Warts; exact disease term.",
    ("D017805", "丧偶"): "Wikidata Q16675060 links the Chinese label to MeSH D017805 Widowhood; exact psychosocial term.",
}

REJECTED = {
    ("D005582", "基金会"): "MeSH's biomedical funding-organization scope is narrower than the generic Chinese label; defer pending a domain-specific glossary.",
    ("D004531", "蛋"): "The Wikidata label is specifically egg as food, while MeSH Eggs is broader; defer rather than imply a one-to-one scope.",
    ("D003250", "缠绕"): "The Chinese label means winding/entangling and does not match the medical/technical MeSH constriction sense.",
    ("D006733", "角"): "角 is ambiguous and does not distinguish anatomical horns from several unrelated senses.",
    ("D014341", "董事"): "董事 is a board director, not a reliable translation for trustee.",
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


def load_inputs() -> tuple[dict, dict[str, dict[str, str]], list[dict[str, str]], dict[str, dict]]:
    if sha(LABELS.read_bytes()) != LABELS_SHA256:
        raise SystemExit("Wikidata MeSH label snapshot SHA-256 mismatch")
    if sha(ENTITIES.read_bytes()) != ENTITIES_SHA256:
        raise SystemExit("Wikidata entity revision snapshot SHA-256 mismatch")
    if sha(MESH_ARCHIVE.read_bytes()) != MESH_SHA256:
        raise SystemExit("NLM MeSH 2026 archive SHA-256 mismatch")

    sys.path.insert(0, str(ROOT / "scripts"))
    import build_mesh_medical_batch as mesh_batch

    inputs = mesh_batch.load_inputs()
    for line in (DATA / "mesh-medical-expansion.tsv").read_text(encoding="utf-8").splitlines():
        chinese, english, _pos, _source = line.split("\t")
        inputs["pairs"].add((chinese, english))
        inputs["extras"][chinese] = inputs["extras"].get(chinese, 0) + 1
    mesh_expansion = DATA / "mesh-medical-expansion.tsv"
    mesh_tags = DATA / "mesh-medical-tags.tsv"
    inputs["mesh_input_hashes"][mesh_expansion.name] = sha(mesh_expansion.read_bytes())
    inputs["mesh_input_hashes"][mesh_tags.name] = sha(mesh_tags.read_bytes())
    existing_mesh_words = set()
    existing_mesh_tags = set()
    for line in mesh_expansion.read_text(encoding="utf-8").splitlines():
        _chinese, english, _pos, _source = line.split("\t")
        existing_mesh_words.add(english.casefold())
    for line in mesh_tags.read_text(encoding="utf-8").splitlines():
        english, _mask, _source = line.split("\t")
        existing_mesh_tags.add(english.casefold())
    inputs["runtime_existing_words"] = inputs["words"] | existing_mesh_words
    inputs["existing_medical_tags"].update(existing_mesh_tags)

    descriptors, _ = mesh_batch.read_mesh()
    mesh_by_id = {row["mesh_id"]: row for row in descriptors}
    labels_data = json.loads(LABELS.read_text(encoding="utf-8"))
    entity_data = json.loads(ENTITIES.read_text(encoding="utf-8"))["entities"]
    return inputs, mesh_by_id, labels_data, entity_data


def discover(inputs: dict, mesh_by_id: dict[str, dict[str, str]], labels_data: list[dict],
             entity_data: dict[str, dict]) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in labels_data:
        mesh_id = row.get("mesh", {}).get("value", "")
        lang = row.get("zh", {}).get("xml:lang", "")
        if mesh_id in mesh_by_id and lang in LANG_PRIORITY:
            grouped[(mesh_id, row["zh"]["value"])].append(row)

    ipa_words = inputs["uk"] | inputs["us"]
    candidates = []
    for (mesh_id, chinese), rows in grouped.items():
        descriptor = mesh_by_id[mesh_id]
        english = descriptor["english"].casefold()
        if english in inputs["words"] or english not in ipa_words:
            continue
        if chinese not in inputs["pinyin"]:
            continue
        if not any(pos == "n." for _gloss, pos in inputs["ecdict"].get(english, set())):
            continue
        if inputs["extras"].get(chinese, 0) >= 8:
            continue
        if (chinese, english) in inputs["pairs"]:
            continue

        source_rows = sorted(
            rows,
            key=lambda row: (
                LANG_PRIORITY.index(row["zh"]["xml:lang"]),
                row["item"]["value"],
                row.get("en", {}).get("value", ""),
            ),
        )
        qids = {row["item"]["value"].rsplit("/", 1)[-1] for row in source_rows}
        if len(qids) != 1:
            raise SystemExit(f"Ambiguous Wikidata item mapping for {mesh_id}: {chinese}: {sorted(qids)}")
        qid = next(iter(qids))
        entity = entity_data.get(qid)
        if entity is None or mesh_id not in entity["mesh_ids"]:
            raise SystemExit(f"Wikidata entity lacks the exact MeSH P486 assertion: {qid} / {mesh_id}")
        chosen = source_rows[0]
        lang = chosen["zh"]["xml:lang"]
        label = chosen["zh"]["value"]
        if entity["labels"].get(lang) != label:
            raise SystemExit(f"Wikidata label differs from pinned entity revision: {qid} / {lang}")
        wikidata_english = chosen.get("en", {}).get("value", "")
        if not wikidata_english:
            wikidata_english = entity["labels"].get("en", "")
        pinyin, frequency = inputs["pinyin"][chinese]
        candidates.append({
            "mesh_id": mesh_id,
            "mesh_english": descriptor["english"],
            "chinese": chinese,
            "wikidata_qid": qid,
            "wikidata_english": wikidata_english,
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
            note = "MeSH/Wikidata 直连关系可核验，但术语过宽、语域不够专业或医学用途不够明确；待找到更精确词表再判断。"
        reviewed.append({**row, "decision": decision, "review_note": note})
    if set(ACCEPTED) - seen or set(REJECTED) - seen:
        missing = (set(ACCEPTED) | set(REJECTED)) - seen
        raise SystemExit(f"Curated Wikidata decisions are absent from candidates: {sorted(missing)}")
    return reviewed


def build(candidates: list[dict[str, str]], reviewed: list[dict[str, str]], inputs: dict) -> dict:
    candidate_bytes = write_tsv(CANDIDATES, CANDIDATE_FIELDS, candidates)
    reviewed_bytes = write_tsv(REVIEWED, REVIEW_FIELDS, reviewed)
    accepted = [row for row in reviewed if row["decision"] == "accept"]
    expansion_rows = [
        {"chinese": row["chinese"], "english": row["mesh_english"].casefold(), "pos": "n.", "source": SOURCE}
        for row in accepted
    ]
    expansion_rows.sort(key=lambda row: (row["chinese"], row["english"]))
    accepted_words = {row["mesh_english"].casefold() for row in accepted}
    tag_words = sorted(accepted_words - inputs["existing_medical_tags"])
    tag_rows = [{"english": word, "mask": str(MEDICAL_BIT), "source": SOURCE} for word in tag_words]
    expansion_bytes = write_tsv(EXPANSION, ("chinese", "english", "pos", "source"), expansion_rows, header=False)
    tag_bytes = write_tsv(TAGS, ("english", "mask", "source"), tag_rows, header=False)

    source_hashes = {
        LABELS.name: sha(LABELS.read_bytes()),
        ENTITIES.name: sha(ENTITIES.read_bytes()),
        "NLM-MeSH-2026-desc.zip": MESH_SHA256,
    }
    label_query_rows = len(json.loads(LABELS.read_text(encoding="utf-8")))
    entity_revision_records = len(json.loads(ENTITIES.read_text(encoding="utf-8"))["entities"])
    manifest = {
        "batch": "22-wikidata-mesh-medical",
        "sources": [
            {"name": "Wikidata structured data", "license": "CC0 1.0", "url": "https://www.wikidata.org/wiki/Wikidata:Licensing"},
            {"name": "NLM Medical Subject Headings (MeSH), 2026", "terms": "Free use with NLM attribution and version identification", "url": "https://www.nlm.nih.gov/databases/download/terms_and_conditions_mesh.html"},
        ],
        "wikidata_snapshot": {
            "retrieved_at_utc": "2026-10-07",
            "query_endpoint": "https://query.wikidata.org/sparql",
            "label_query_rows": label_query_rows,
            "entity_revision_records": entity_revision_records,
        },
        "translation_method": "Chinese label and MeSH descriptor are joined by the exact Wikidata P486 external identifier. The runtime adds no definitions, examples, or unreviewed labels.",
        "candidate_filter": "Existing pinyin key; local UK or US IPA for the MeSH preferred term; ECDICT noun POS evidence; spare per-key capacity; no duplicate mapping; entity revision independently confirms the same P486 MeSH ID and language label.",
        "source_sha256": source_hashes,
        "runtime_input_sha256": inputs["mesh_input_hashes"],
        "candidates": len(candidates),
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
            REVIEWED.relative_to(DATA).as_posix(): {"rows": len(reviewed), "sha256": sha(reviewed_bytes)},
        },
        "runtime_note": "The runtime compiles only short reviewed mappings and compact medical tag rows; CC0 source snapshots and audit tables are not loaded during typing.",
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discover", action="store_true")
    args = parser.parse_args()
    inputs, mesh_by_id, labels_data, entity_data = load_inputs()
    candidates = discover(inputs, mesh_by_id, labels_data, entity_data)
    if args.discover:
        print(json.dumps({"eligible_candidates": len(candidates), "candidate_headwords": len({row['mesh_english'] for row in candidates})}, ensure_ascii=False, indent=2))
        return
    manifest = build(candidates, review(candidates), inputs)
    print(json.dumps({key: manifest[key] for key in ("candidates", "accepted_mappings", "accepted_new_english_headwords", "rejected_candidates", "deferred_candidates", "new_medical_tag_memberships")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
