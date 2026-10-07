"""Build a conservative medical vocabulary tranche from NLM MeSH 2026.

MeSH supplies English scope and descriptor hierarchy only. New Mandarin glosses
must independently match the pinned ECDICT short gloss/POS, local pinyin and
IPA, then pass the reviewed decision table below. Runtime data never loads the
full MeSH XML or the research/audit tables.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
SOURCE_ARCHIVE = DATA / "sources/mesh/desc2026.zip"
SOURCE_SHA256 = "bb73dfdfe78cbfcd692ef399bb6df24750327ff62c4f53574826c56ba3d6a3f3"
SOURCE_URL = "https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/xmlmesh/desc2026.zip"
SOURCE = "NLM MeSH 2026"
MAPPING_SOURCE = "NLM MeSH 2026 + ECDICT MIT"
MEDICAL_BIT = 1 << 8
MAX_EXTRA_PER_KEY = 8

CANDIDATES = DATA / "batches/21-mesh-medical-candidates.tsv"
REVIEWED = DATA / "batches/21-mesh-medical-reviewed.tsv"
TAG_EVIDENCE = DATA / "batches/21-mesh-medical-tags-evidence.tsv"
EXPANSION = DATA / "mesh-medical-expansion.tsv"
TAGS = DATA / "mesh-medical-tags.tsv"
MANIFEST = DATA / "mesh-medical-manifest.json"

ROOTS = ("A", "C", "D", "E", "F", "G", "N")
WORD = re.compile(r"[a-z][a-z'-]*\Z")
CANDIDATE_FIELDS = (
    "mesh_id", "english", "chinese", "pos", "tree_numbers", "pinyin",
    "pinyin_frequency", "ipa_sources", "ecdict_rows",
)
REVIEW_FIELDS = CANDIDATE_FIELDS + ("decision", "review_note")
TAG_FIELDS = (
    "english", "descriptor_ids", "preferred_terms", "tree_numbers",
    "matched_chinese_keys",
)

# Precise, short ECDICT senses retained after checking the MeSH headword and
# Chinese gloss together. Entries absent here remain deferred, not inferred.
ACCEPTED = {
    ("吸附", "adsorption", "n."): "MeSH adsorption is the surface-binding process; 吸附 is the exact concise scientific gloss.",
    ("等位基因", "alleles", "n."): "Alleles are gene variants; 等位基因 is the established Chinese term.",
    ("脱发", "alopecia", "n."): "Alopecia is hair loss; 脱发 is the direct Chinese term.",
    ("麻醉药", "anesthetics", "n."): "Anesthetics are medicines that produce anesthesia; 麻醉药 is exact.",
    ("窒息", "asphyxia", "n."): "Asphyxia is oxygen deprivation due to impaired breathing; 窒息 is the accepted concise gloss.",
    ("腋窝", "axilla", "n."): "Axilla is the anatomical armpit; 腋窝 is exact.",
    ("放血", "bloodletting", "n."): "Bloodletting is the removal of blood; 放血 is exact.",
    ("尸体", "cadaver", "n."): "A cadaver is a dead body used as an anatomical/medical specimen; 尸体 is the concise gloss.",
    ("结石", "calculi", "n."): "Calculi are pathological stones; 结石 is exact.",
    ("套管", "cannula", "n."): "A cannula is a small tube inserted into the body; 套管 is exact.",
    ("毛细管", "capillaries", "n."): "Capillaries are tiny vessels; 毛细管 is the concise anatomical gloss.",
    ("碳水化合物", "carbohydrates", "n."): "Carbohydrates are a nutrient class; 碳水化合物 is exact.",
    ("阳离子", "cations", "n."): "Cations are positively charged ions; 阳离子 is exact.",
    ("烧灼", "cautery", "n."): "Cautery is tissue destruction by heat or caustic action; 烧灼 is the matching procedure sense.",
    ("细胞", "cells", "n."): "Cells are the basic structural units of living organisms; 细胞 is exact.",
    ("大脑", "cerebrum", "n."): "Cerebrum is the large upper part of the brain; 大脑 is exact.",
    ("锁骨", "clavicle", "n."): "Clavicle is the collarbone; 锁骨 is exact.",
    ("阴沟", "cloaca", "n."): "Cloaca is the shared anatomical passage in some animals; 阴沟 is the exact anatomical gloss.",
    ("性交", "coitus", "n."): "Coitus is sexual intercourse; 性交 is exact.",
    ("收缩", "constriction", "n."): "Constriction is narrowing or tightening; 收缩 is the matching physiological sense.",
    ("挛缩", "contracture", "n."): "Contracture is permanent shortening/tightening of tissue; 挛缩 is exact.",
    ("挫伤", "contusions", "n."): "Contusions are blunt-force injuries; 挫伤 is exact.",
    ("交配", "copulation", "n."): "Copulation is mating; 交配 is exact for the MeSH reproductive concept.",
    ("犬齿", "cuspid", "n."): "Cuspid is a canine tooth; 犬齿 is exact.",
    ("囊肿", "cysts", "n."): "Cysts are closed sac-like structures; 囊肿 is the relevant medical sense.",
    ("头皮屑", "dander", "n."): "Dander is shed skin flakes; 头皮屑 is retained as the concise human-use gloss.",
    ("排便", "defecation", "n."): "Defecation is bowel evacuation; 排便 is exact.",
    ("妄想", "delusions", "n."): "Delusions are fixed false beliefs; 妄想 is exact in the clinical sense.",
    ("登革热", "dengue", "n."): "Dengue is the mosquito-borne disease; 登革热 is exact.",
    ("消毒剂", "disinfectants", "n."): "Disinfectants are agents used to destroy pathogens; 消毒剂 is exact.",
    ("消毒", "disinfection", "n."): "Disinfection is the process of destroying pathogens; 消毒 is exact.",
    ("解剖", "dissection", "n."): "Dissection is systematic anatomical examination; 解剖 is exact.",
    ("脑电图", "electroencephalography", "n."): "Electroencephalography records brain electrical activity; 脑电图 is the conventional concise gloss.",
    ("情绪", "emotions", "n."): "Emotions is the MeSH psychological concept; 情绪 is exact.",
    ("乳剂", "emulsions", "n."): "Emulsions are mixtures of immiscible liquids; 乳剂 is exact in pharmaceutical use.",
    ("流行病", "epidemics", "n."): "Epidemics are disease occurrences above expected levels; 流行病 is the concise established gloss.",
    ("肾上腺素", "epinephrine", "n."): "Epinephrine is the hormone/drug adrenaline; 肾上腺素 is exact.",
    ("呼气", "exhalation", "n."): "Exhalation is breathing air out; 呼气 is exact.",
    ("睫毛", "eyelashes", "n."): "Eyelashes are hairs along the eyelids; 睫毛 is exact.",
    ("眼睑", "eyelids", "n."): "Eyelids are the folds covering the eyes; 眼睑 is exact.",
    ("禁食", "fasting", "n."): "Fasting is abstention from food, including for clinical preparation; 禁食 is exact.",
    ("生殖器", "genitalia", "n."): "Genitalia are reproductive organs; 生殖器 is exact.",
    ("甘油", "glycerol", "n."): "Glycerol is the chemical compound; 甘油 is exact.",
    ("口臭", "halitosis", "n."): "Halitosis is bad breath; 口臭 is exact.",
    ("嘶哑", "hoarseness", "n."): "Hoarseness is an abnormal rough/weak voice; 嘶哑 is exact.",
    ("激素", "hormones", "n."): "Hormones are signaling substances; 激素 is exact.",
    ("增生", "hyperplasia", "n."): "Hyperplasia is an increase in cell number; 增生 is exact.",
    ("肥大", "hypertrophy", "n."): "Hypertrophy is enlargement of an organ/tissue; 肥大 is exact.",
    ("吸入", "inhalation", "n."): "Inhalation is drawing air or substances into the lungs; 吸入 is exact.",
    ("授精", "insemination", "n."): "Insemination is introduction of semen for reproduction; 授精 is exact.",
    ("核素", "isotopes", "n."): "Isotopes are nuclides of the same element; 核素 is the precise scientific gloss.",
    ("关节", "joints", "n."): "Joints are anatomical articulations; 关节 is exact.",
    ("哺乳", "lactation", "n."): "Lactation is milk production/secretion; 哺乳 is the concise clinical gloss.",
    ("性欲", "libido", "n."): "Libido is sexual desire; 性欲 is exact.",
    ("面罩", "masks", "n."): "Masks are face coverings used for protection or clinical procedures; 面罩 is exact.",
    ("咀嚼", "mastication", "n."): "Mastication is chewing; 咀嚼 is exact.",
    ("掌骨", "metacarpus", "n."): "Metacarpus is the palm-bone region; 掌骨 is exact.",
    ("矿物", "minerals", "n."): "Minerals are inorganic nutrients/substances; 矿物 is the concise MeSH sense.",
    ("护士", "nurses", "n."): "Nurses are health professionals; 护士 is exact.",
    ("药膏", "ointments", "n."): "Ointments are semisolid topical preparations; 药膏 is exact.",
    ("药房", "pharmacies", "n."): "Pharmacies are places where medicines are dispensed; 药房 is exact.",
    ("医生", "physicians", "n."): "Physicians are medical doctors; 医生 is exact.",
    ("中毒", "poisoning", "n."): "Poisoning is harmful exposure to a toxic substance; 中毒 is exact.",
    ("刺伤", "punctures", "n."): "Punctures are injuries caused by pointed objects; 刺伤 is exact.",
    ("发抖", "shivering", "n."): "Shivering is involuntary trembling, often associated with cold or fever; 发抖 is exact.",
    ("口吃", "stuttering", "n."): "Stuttering is a speech fluency disorder; 口吃 is exact.",
    ("缝合", "sutures", "n."): "Sutures are stitches/material used to close wounds; 缝合 is the procedural gloss.",
    ("突触", "synapses", "n."): "Synapses are junctions between neurons; 突触 is exact.",
    ("温度计", "thermometers", "n."): "Thermometers measure temperature, including clinical temperature; 温度计 is exact.",
    ("组织", "tissues", "n."): "Tissues are groups of cells with a common function; 组织 is exact in anatomy.",
    ("无意识", "unconsciousness", "n."): "Unconsciousness is loss of awareness; 无意识 is exact.",
    ("疫苗", "vaccines", "n."): "Vaccines are preparations that induce immunity; 疫苗 is exact.",
    ("牛痘", "vaccinia", "n."): "Vaccinia is the orthopoxvirus historically used for smallpox vaccination; 牛痘 is exact.",
    ("颧骨", "zygoma", "n."): "Zygoma is the cheekbone; 颧骨 is exact.",
    ("合子", "zygote", "n."): "A zygote is a fertilized cell; 合子 is exact.",
    ("受精卵", "zygote", "n."): "A zygote is a fertilized cell; 受精卵 is an exact common equivalent.",
}

REJECTED = {
    ("扁桃体", "amygdala", "n."): "扁桃体 means tonsil; amygdala is 杏仁核, so this ECDICT gloss is a false friend.",
    ("太空舱", "capsules", "n."): "太空舱 is the spacecraft sense, not medical capsules.",
    ("膀胱", "cysts", "n."): "膀胱 means urinary bladder, not cysts.",
    ("灯丝", "ligaments", "n."): "灯丝 means filament, unrelated to ligaments.",
    ("镇静剂", "pacifiers", "n."): "镇静剂 is a sedative; pacifiers are soothing devices, not this medicine.",
    ("纹理", "veins", "n."): "纹理 is texture; it is not the anatomical meaning of veins.",
    ("缺点", "warts", "n."): "缺点 is a figurative meaning of wart and is misleading as a medical gloss.",
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


def relevant_tree_numbers(tree_numbers: list[str]) -> list[str]:
    return sorted({tree for tree in tree_numbers
                   if tree and tree[0] in ROOTS and not tree.startswith("G17")})


def read_mesh() -> tuple[list[dict[str, str]], dict[str, dict[str, set[str]]]]:
    if not SOURCE_ARCHIVE.is_file():
        raise SystemExit(f"Missing pinned NLM MeSH 2026 archive: {SOURCE_ARCHIVE}")
    archive_bytes = SOURCE_ARCHIVE.read_bytes()
    if sha(archive_bytes) != SOURCE_SHA256:
        raise SystemExit("NLM MeSH archive SHA-256 mismatch")
    descriptors = []
    term_index: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"ids": set(), "preferred": set(), "trees": set()}
    )
    with zipfile.ZipFile(SOURCE_ARCHIVE) as archive:
        if archive.namelist() != ["desc2026.xml"]:
            raise SystemExit("Unexpected files in pinned MeSH archive")
        with archive.open("desc2026.xml") as xml_file:
            for _, record in ET.iterparse(xml_file, events=("end",)):
                if record.tag != "DescriptorRecord":
                    continue
                mesh_id = record.findtext("DescriptorUI", default="").strip()
                preferred = record.findtext("DescriptorName/String", default="").strip()
                all_trees = [node.text.strip() for node in record.findall("TreeNumberList/TreeNumber") if node.text]
                trees = relevant_tree_numbers(all_trees)
                if not mesh_id or not preferred or not trees:
                    record.clear()
                    continue
                descriptors.append({"mesh_id": mesh_id, "english": preferred, "tree_numbers": ",".join(trees)})
                labels = {preferred}
                labels.update(
                    node.text.strip()
                    for node in record.findall("ConceptList/Concept/TermList/Term/String")
                    if node.text and node.text.strip()
                )
                for label in labels:
                    normalized = " ".join(label.casefold().split())
                    if not normalized:
                        continue
                    entry = term_index[normalized]
                    entry["ids"].add(mesh_id)
                    entry["preferred"].add(preferred)
                    entry["trees"].update(trees)
                record.clear()
    return descriptors, term_index


def load_inputs() -> dict:
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_computerese_batch as computerese

    inputs = computerese.load_inputs()
    # Batch 20 is the latest compiled shared vocabulary tranche. Include it in
    # reachability and capacity checks without changing the original input set.
    batch20_expansion = DATA / "computerese-expansion.tsv"
    for line in batch20_expansion.read_text(encoding="utf-8").splitlines():
        chinese, english, _pos, _source = line.split("\t")
        pair = (chinese, english)
        if pair not in inputs["pairs"]:
            inputs["pairs"].add(pair)
            inputs["extras"][chinese] = inputs["extras"].get(chinese, 0) + 1
        inputs["words"].add(english)

    existing_medical = set()
    professional_tags = DATA / "professional-domain-tags.tsv"
    for line in professional_tags.read_text(encoding="utf-8").splitlines():
        fields = line.split("\t")
        if len(fields) >= 2 and int(fields[1]) & MEDICAL_BIT:
            existing_medical.add(fields[0].casefold())

    input_hashes = dict(inputs["hashes"])
    input_hashes["computerese-expansion.tsv"] = sha(batch20_expansion.read_bytes())
    input_hashes["professional-domain-tags.tsv"] = sha(professional_tags.read_bytes())
    inputs["existing_medical_tags"] = existing_medical
    inputs["mesh_input_hashes"] = input_hashes
    return inputs


def discover(inputs: dict, descriptors: list[dict[str, str]], term_index: dict[str, dict[str, set[str]]]):
    candidate_rows = []
    ecdict_by_word: dict[str, list[tuple[str, set[str]]]] = defaultdict(list)
    ipa_words = inputs["uk"] | inputs["us"]
    for english, gloss_positions in inputs["ecdict"].items():
        by_gloss: dict[str, set[str]] = defaultdict(set)
        for chinese, pos in gloss_positions:
            by_gloss[chinese].add(pos)
        ecdict_by_word[english].extend(by_gloss.items())
    mapped_keys: dict[str, set[str]] = defaultdict(set)
    for chinese, english in inputs["pairs"]:
        normalized = english.casefold()
        if chinese in inputs["pinyin"]:
            mapped_keys[normalized].add(chinese)

    for descriptor in descriptors:
        english = descriptor["english"].casefold()
        if not WORD.fullmatch(english) or english in inputs["words"]:
            continue
        if english not in ipa_words:
            continue
        for chinese, positions in ecdict_by_word.get(english, ()):
            if chinese not in inputs["pinyin"]:
                continue
            for pos in sorted(positions):
                if pos != "n.":
                    continue
                if inputs["extras"].get(chinese, 0) >= MAX_EXTRA_PER_KEY:
                    continue
                if (chinese, english) in inputs["pairs"]:
                    continue
                candidate_rows.append({
                    "mesh_id": descriptor["mesh_id"],
                    "english": english,
                    "chinese": chinese,
                    "pos": pos,
                    "tree_numbers": descriptor["tree_numbers"],
                    "pinyin": inputs["pinyin"][chinese][0],
                    "pinyin_frequency": str(inputs["pinyin"][chinese][1]),
                    "ipa_sources": ",".join(label for label, present in (("UK", english in inputs["uk"]), ("US", english in inputs["us"])) if present),
                    "ecdict_rows": ",".join(map(str, sorted(inputs["ecdict_rows"].get((english, chinese, pos), set())))),
                })
    candidate_rows.sort(key=lambda row: (row["english"], row["chinese"], row["pos"], row["mesh_id"]))

    def matched_keys(english: str, extra_pairs: set[tuple[str, str]] = set()) -> set[str]:
        result = set(mapped_keys.get(english, set()))
        result.update(chinese for chinese, word in extra_pairs if word == english and chinese in inputs["pinyin"])
        return result

    preferred_index: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"ids": set(), "preferred": set(), "trees": set()}
    )
    for descriptor in descriptors:
        english = descriptor["english"].casefold()
        evidence = preferred_index[english]
        evidence["ids"].add(descriptor["mesh_id"])
        evidence["preferred"].add(descriptor["english"])
        evidence["trees"].update(descriptor["tree_numbers"].split(","))

    tag_rows = []
    for english, evidence in sorted(preferred_index.items()):
        if english not in mapped_keys:
            continue
        keys = matched_keys(english)
        if not keys or english in inputs["existing_medical_tags"]:
            continue
        tag_rows.append({
            "english": english,
            "descriptor_ids": ",".join(sorted(evidence["ids"])),
            "preferred_terms": " | ".join(sorted(evidence["preferred"])),
            "tree_numbers": ",".join(sorted(evidence["trees"])),
            "matched_chinese_keys": " | ".join(sorted(keys)),
        })
    return candidate_rows, tag_rows


def bootstrap_review(candidate_rows: list[dict[str, str]]) -> None:
    if CANDIDATES.exists() or REVIEWED.exists():
        raise SystemExit("Refusing to overwrite existing MeSH candidate/review decisions")
    candidates = write_tsv(CANDIDATES, CANDIDATE_FIELDS, candidate_rows)
    reviewed = []
    for row in candidate_rows:
        key = (row["chinese"], row["english"], row["pos"])
        if key in ACCEPTED:
            decision, note = "accept", ACCEPTED[key]
        elif key in REJECTED:
            decision, note = "reject", REJECTED[key]
        else:
            decision = "defer"
            note = "暂不采用：ECDICT 的一般短义不足以确认它与该 MeSH 医学概念完全对应，保留候选以待更精确的中英术语来源。"
        reviewed.append({**row, "decision": decision, "review_note": note})
    write_tsv(REVIEWED, REVIEW_FIELDS, reviewed)
    print(f"Wrote {len(candidate_rows)} MeSH/ECDICT candidates and {len(reviewed)} explicit decisions")


def read_review(candidate_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not CANDIDATES.is_file() or not REVIEWED.is_file():
        raise SystemExit("Missing candidate/review files; run with --bootstrap-review first")
    with CANDIDATES.open(encoding="utf-8", newline="") as stream:
        source_rows = list(csv.DictReader(stream, delimiter="\t"))
    if tuple(source_rows[0].keys()) != CANDIDATE_FIELDS or source_rows != candidate_rows:
        raise SystemExit("MeSH candidate evidence differs from the current pinned inputs")
    with REVIEWED.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if tuple(reader.fieldnames or ()) != REVIEW_FIELDS:
            raise SystemExit("Unexpected MeSH review columns")
        reviewed = list(reader)
    expected = {(row["mesh_id"], row["chinese"], row["english"], row["pos"]): row for row in candidate_rows}
    decisions = {}
    for row in reviewed:
        key = (row["mesh_id"], row["chinese"], row["english"], row["pos"])
        if key not in expected or key in decisions:
            raise SystemExit(f"Duplicate or stale MeSH review decision: {key}")
        for field in CANDIDATE_FIELDS:
            if row[field] != expected[key][field]:
                raise SystemExit(f"MeSH candidate evidence changed for {key}: {field}")
        if row["decision"] not in {"accept", "reject", "defer"} or not row["review_note"].strip():
            raise SystemExit(f"Invalid or unexplained MeSH review decision: {key}")
        if row["decision"] == "accept" and (row["chinese"], row["english"], row["pos"]) not in ACCEPTED:
            raise SystemExit(f"Accepted MeSH mapping lacks a checked rationale: {key}")
        decisions[key] = row
    if set(decisions) != set(expected):
        raise SystemExit(f"Incomplete MeSH review: missing {len(set(expected) - set(decisions))} decisions")
    return list(decisions.values())


def build(candidate_rows: list[dict[str, str]], tag_candidates: list[dict[str, str]], inputs: dict,
          descriptors: list[dict[str, str]], archive_sha256: str) -> dict[Path, bytes]:
    reviewed = read_review(candidate_rows)
    accepted = [row for row in reviewed if row["decision"] == "accept"]
    extras: dict[str, int] = defaultdict(int)
    expansion_rows = []
    accepted_pairs = set()
    for row in accepted:
        chinese, english, pos = row["chinese"], row["english"], row["pos"]
        pair = (chinese, english)
        if pair in inputs["pairs"] or chinese not in inputs["pinyin"]:
            raise SystemExit(f"Accepted MeSH mapping already exists or lacks pinyin: {chinese} -> {english}")
        extras[chinese] += 1
        if inputs["extras"].get(chinese, 0) + extras[chinese] > MAX_EXTRA_PER_KEY:
            raise SystemExit(f"Accepted MeSH mappings exceed per-key capacity for {chinese}")
        accepted_pairs.add(pair)
        expansion_rows.append({"chinese": chinese, "english": english, "pos": pos, "source": MAPPING_SOURCE})
    expansion_rows.sort(key=lambda row: (row["chinese"], row["english"], row["pos"]))

    # Newly accepted headwords become taggable through the same MeSH hierarchy.
    candidate_tag_by_word = {row["english"]: row for row in tag_candidates}
    accepted_words = {row["english"] for row in accepted}
    _, term_index = read_mesh()
    new_tag_words = set(candidate_tag_by_word) | {
        word for word in accepted_words
        if word in term_index and word not in inputs["existing_medical_tags"]
    }
    tag_rows = [{"english": word, "mask": str(MEDICAL_BIT), "source": SOURCE} for word in sorted(new_tag_words)]
    tag_evidence_rows = [candidate_tag_by_word[word] for word in sorted(candidate_tag_by_word)]
    for word in sorted(accepted_words - set(candidate_tag_by_word)):
        evidence = term_index.get(word)
        if evidence is None:
            raise SystemExit(f"Accepted MeSH word has no descriptor term evidence: {word}")
        tag_evidence_rows.append({
            "english": word,
            "descriptor_ids": ",".join(sorted(evidence["ids"])),
            "preferred_terms": " | ".join(sorted(evidence["preferred"])),
            "tree_numbers": ",".join(sorted(evidence["trees"])),
            "matched_chinese_keys": " | ".join(sorted(row["chinese"] for row in accepted if row["english"] == word)),
        })
    tag_evidence_rows.sort(key=lambda row: row["english"])

    expansion_bytes = write_tsv(EXPANSION, ("chinese", "english", "pos", "source"), expansion_rows, header=False)
    tags_bytes = write_tsv(TAGS, ("english", "mask", "source"), tag_rows, header=False)
    evidence_bytes = write_tsv(TAG_EVIDENCE, TAG_FIELDS, tag_evidence_rows)
    reviewed_bytes = REVIEWED.read_bytes()
    candidate_bytes = CANDIDATES.read_bytes()
    newly_tagged = len(set(new_tag_words) - inputs["existing_medical_tags"])
    manifest = {
        "batch": "21-nlm-mesh-medical",
        "source": {
            "name": "NLM Medical Subject Headings (MeSH), 2026 Descriptor XML",
            "url": SOURCE_URL,
            "version": "2026",
            "license_terms": "Free use with NLM attribution and version identification; see official terms URL in MESH-ATTRIBUTION.md.",
            "archive_sha256": archive_sha256,
            "descriptor_records_in_selected_tree_scope": len(descriptors),
            "tree_scope": list(ROOTS),
            "excluded_tree_branch": "G17 mathematics concepts",
        },
        "translation_provenance": "MeSH supplies English descriptor labels and medical-topic scope only. Chinese mappings come from exact ECDICT MIT short gloss/POS matches and are individually accepted only when the English concept and Chinese gloss agree.",
        "runtime_inputs_sha256": inputs["mesh_input_hashes"],
        "candidate_mappings_with_pinyin_ipa_and_exact_ecdict": len(candidate_rows),
        "accepted_new_mappings": len(accepted),
        "accepted_new_english_headwords": len(accepted_words - inputs["words"]),
        "rejected_candidates": sum(row["decision"] == "reject" for row in reviewed),
        "deferred_candidates": sum(row["decision"] == "defer" for row in reviewed),
        "new_medical_tag_memberships": newly_tagged,
        "tag_candidates_have_runtime_chinese_mapping_and_pinyin": len(tag_candidates),
        "tag_memberships_are_automatic_meSH_tree_intersections": True,
        "mapping_rows": [f"{row['chinese']} -> {row['english']} ({row['pos']})" for row in expansion_rows],
        "outputs": {
            EXPANSION.name: {"rows": len(expansion_rows), "sha256": sha(expansion_bytes)},
            TAGS.name: {"rows": len(tag_rows), "sha256": sha(tags_bytes)},
            REVIEWED.relative_to(DATA).as_posix(): {"rows": len(reviewed), "sha256": sha(reviewed_bytes)},
            CANDIDATES.relative_to(DATA).as_posix(): {"rows": len(candidate_rows), "sha256": sha(candidate_bytes)},
            TAG_EVIDENCE.relative_to(DATA).as_posix(): {"rows": len(tag_evidence_rows), "sha256": sha(evidence_bytes)},
        },
        "runtime_note": "The runtime includes only reviewed short mappings and compact tag memberships. It does not load the MeSH XML, definitions, or audit tables; tags use the English descriptor hierarchy and do not claim complete medical-vocabulary coverage.",
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return {EXPANSION: expansion_bytes, TAGS: tags_bytes, TAG_EVIDENCE: evidence_bytes}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--bootstrap-review", action="store_true")
    args = parser.parse_args()
    inputs = load_inputs()
    descriptors, term_index = read_mesh()
    candidate_rows, tag_candidates = discover(inputs, descriptors, term_index)
    if args.discover:
        print(json.dumps({
            "selected_mesh_descriptors": len(descriptors),
            "unique_selected_mesh_terms_including_synonyms": len(term_index),
            "unique_selected_preferred_terms": len({row["english"].casefold() for row in descriptors}),
            "candidate_new_mappings": len(candidate_rows),
            "tag_candidates_with_runtime_chinese_and_pinyin": len(tag_candidates),
            "new_tag_memberships_before_candidates": len(tag_candidates),
        }, ensure_ascii=False, indent=2))
    elif args.bootstrap_review:
        bootstrap_review(candidate_rows)
    else:
        outputs = build(candidate_rows, tag_candidates, inputs, descriptors, SOURCE_SHA256)
        for path, content in outputs.items():
            print(f"{path.relative_to(ROOT)}: {len(content)} bytes")
        print(f"{MANIFEST.relative_to(ROOT)}: {MANIFEST.stat().st_size} bytes")


if __name__ == "__main__":
    main()
