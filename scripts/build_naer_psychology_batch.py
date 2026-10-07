"""Build the reviewed NAER psychology vocabulary tranche."""
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
SOURCE_CSV = DATA / "sources/naer/psychology-academic-terms-2026-08-12.csv"
SOURCE_METADATA = DATA / "sources/naer/psychology-dataset.json"
SOURCE_SHA256 = "d603fce3628389aa849c73f1af4104653357e715fb82946e35b67507d992f166"
PREFILTER = DATA / "batches/36-naer-psychology-prefilter.tsv"
CANDIDATES = DATA / "batches/36-naer-psychology-candidates.tsv"
REVIEWED = DATA / "batches/36-naer-psychology-reviewed.tsv"
TAG_REVIEWED = DATA / "batches/36-naer-psychology-tags-reviewed.tsv"
EXPANSION = DATA / "naer-psychology-expansion.tsv"
TAGS = DATA / "naer-psychology-tags.tsv"
MANIFEST = DATA / "naer-psychology-manifest.json"

SOURCE = "NAER Psychology Terminology OGDL v1.0"
PSYCHOLOGY_BIT = 1 << 11
WORD = re.compile(r"[a-z][a-z'-]*\Z")
VARIANT_SEPARATOR = re.compile(r"[；;、，,/／|]+")

PREFILTER_FIELDS = (
    "english", "chinese", "source_chinese", "source_records", "source_urls",
    "pinyin", "pinyin_frequency", "ipa_sources", "ecdict_exact_noun_glosses",
    "already_mapped", "existing_headword", "spare_capacity",
)
REVIEW_FIELDS = PREFILTER_FIELDS + ("decision", "review_note")
TAG_FIELDS = ("english", "source_records", "source_pairs", "already_psychology_tag", "decision", "review_note")

ACCEPTED_PAIRS = {
    ("一致", "congruence"), ("人道主义", "humanism"), ("介入", "intervention"),
    ("仪式", "ritual"), ("保持", "retention"), ("保留", "retention"),
    ("催眠术", "mesmerism"), ("僵局", "impasse"), ("公平", "justice"),
    ("再现", "reproduction"), ("分离", "dissociation"), ("分离", "separation"),
    ("判断", "judgement"), ("压力", "stress"), ("变换", "transformation"),
    ("同情", "sympathy"), ("同意", "consent"), ("和谐", "congruence"),
    ("咨询", "consultation"), ("哀悼", "mourning"), ("善行", "beneficence"),
    ("复制", "reproduction"), ("复原", "recovery"), ("妒忌", "jealousy"),
    ("存在", "being"), ("孤立", "isolation"), ("学习", "learning"),
    ("宣传", "propaganda"), ("容忍", "tolerance"), ("寂寞", "loneliness"),
    ("对比", "contrast"), ("少数民族", "minority"), ("尿床", "enuresis"),
    ("平均数", "mean"), ("归因", "attribution"), ("惩罚", "punishment"),
    ("忠诚", "loyalty"), ("忽略", "neglect"), ("悲伤", "sadness"),
    ("悲观", "pessimism"), ("情感", "affection"), ("抑制", "inhibition"),
    ("折射", "refraction"), ("指导", "guidance"), ("损伤", "impairment"),
    ("损害", "impairment"), ("排斥", "ostracism"), ("接纳", "acceptance"),
    ("放大", "amplification"), ("放逐", "ostracism"), ("期望", "expectancy"),
    ("欺骗", "deception"), ("沮丧", "depression"), ("混淆", "confusion"),
    ("温暖", "warmth"), ("烙印", "stigma"), ("犯罪", "criminality"),
    ("理解", "comprehension"), ("痛苦", "distress"), ("相关", "correlation"),
    ("真诚", "genuineness"), ("磋商", "negotiation"), ("禁欲", "abstinence"),
    ("移动", "locomotion"), ("精神", "psyche"), ("羞怯", "shyness"),
    ("群众", "crowd"), ("节食", "dieting"), ("行动", "act"),
    ("衰退", "deterioration"), ("解构", "deconstruction"), ("解释", "interpretation"),
    ("警戒", "vigilance"), ("认同", "identification"), ("论证", "argument"),
    ("评估", "evaluation"), ("误解", "misconception"), ("说话", "speech"),
    ("调停", "mediation"), ("贬抑", "abasement"), ("超越", "transcendence"),
    ("转换", "transition"), ("迁移", "transfer"), ("逃避", "avoidance"),
    ("道德", "moral"), ("镇静剂", "depressant"), ("镇静剂", "tranquillizer"),
    ("雇用", "employment"), ("顺从", "compliance"), ("预期", "expectancy"),
}
REJECTED_PAIRS = {
    ("介入", "interposition"): "Interposition names an object positioned in front of another (a visual depth cue), not intervention/介入; the ECDICT synonym alone is too broad.",
    ("作业", "exercise"): "In this pair 作业 means an assignment/homework; exercise as a psychological construct or physical activity is not an exact translation.",
    ("分裂", "fission"): "Fission is a biological division process; it is not a precise psychology translation for generic 分裂.",
    ("命运", "karma"): "Karma is a culturally specific doctrine of moral causation, not the general Chinese meaning 命运.",
    ("干涉", "interposition"): "Interposition is a visual depth cue, not the broad Chinese meaning 干涉.",
    ("性行为", "sexuality"): "Sexuality is broader than a particular sexual behavior and does not precisely translate 性行为.",
    ("慈善", "beneficence"): "慈善 means charity/charitable activity; beneficence is the ethical principle of doing good, so these are not interchangeable.",
    ("显性", "dominance"): "Dominance is not a safe translation for 显性, which commonly denotes a dominant genetic trait or an explicit property depending on context.",
    ("果蝇", "drosophila"): "Drosophila is a research organism, but 果蝇 is not a useful human-psychology translation pair for this target.",
    ("核心", "cores"): "The English entry is plural and its exact noun sense does not establish a standalone psychology term corresponding to 核心.",
    ("禁令", "injunction"): "An injunction is a legal order; 禁令 is too broad and the source does not establish a psychology-specific meaning.",
    ("蒸馏", "distillation"): "Distillation is a chemical/industrial process, not a psychology term in the supplied pair.",
    ("表达", "voice"): "Voice does not mean the broad nominal concept 表达; the source/local pair is not an exact translation.",
    ("调停", "intervention"): "Intervention means a deliberate intervening action; 调停 specifically means mediation and is not equivalent in this pair.",
    ("连接", "connections"): "The English item is plural and the generic relation sense does not establish a standalone psychology mapping for 连接.",
    ("驱魔", "exorcism"): "Exorcism is a religious ritual/practice; the translation is outside the intended psychology term mapping.",
}
DEFERRED_PAIRS = {
    ("伪装", "camouflage"): "Could describe masking behavior in psychology, but the source/local pair is too general to distinguish that from ordinary concealment; defer.",
    ("变异", "variance"): "Variance is normally 方差/变异数 in psychometrics; the broad gloss 变异 is not sufficiently exact; defer.",
    ("分离", "separation"): "分离 has only one remaining runtime expansion slot; retain the more specific dissociation mapping and defer this broader alternative under the per-key cap.",
    ("处罚", "punishment"): "The translation can be valid in behavioral psychology but 处罚 is often legal/administrative; defer pending narrower context.",
    ("忠实", "fidelity"): "Psychological treatment/test fidelity is usually 忠实度 or 保真度; bare 忠实 is a broad gloss, so defer.",
    ("忠诚", "fidelity"): "The relevant psychometric/treatment sense is usually 忠实度, while 忠诚 suggests interpersonal loyalty; defer.",
    ("摄取", "ingestion"): "This is an exact nutrition/physiology gloss but the source does not establish a psychology-specific usage; defer.",
    ("特殊化", "specialization"): "Specialization can be a psychology topic, but 特殊化 is an awkward broad mapping without a clear term-level match; defer.",
    ("特殊性", "specificity"): "In psychological measurement specificity is usually 特异性; the broad surface gloss 特殊性 is ambiguous; defer.",
    ("监督", "surveillance"): "Surveillance can mean monitoring in research, but 监督 more often maps to supervision/oversight; defer without context.",
    ("线索", "cues"): "The source uses a plural English form and the local gloss is broad; the singular psychological term cue is not supplied, so defer.",
    ("胜算", "odds"): "Odds is a statistical/probability term, while 胜算 is context-specific and not a stable general psychology translation; defer.",
    ("过程", "course"): "Course can mean a process, but the gloss is broad and the source does not establish a distinct psychology term; defer.",
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
        raise SystemExit("Pinned NAER psychology CSV SHA-256 mismatch")
    metadata = json.loads(SOURCE_METADATA.read_text(encoding="utf-8-sig"))
    if metadata.get("dataset_id") != "15167" or metadata.get("snapshot_sha256") != SOURCE_SHA256:
        raise SystemExit("Unexpected NAER psychology dataset metadata")

    sys.path.insert(0, str(ROOT / "scripts"))
    import build_naer_management_batch as management_batch

    inputs = management_batch.load_inputs(exclude_runtime_files={EXPANSION.name})
    lib_source = (ROOT / "vocabulary/src/lib.rs").read_text(encoding="utf-8")
    tag_files = sorted(set(re.findall(r'include_str!\("\.\./data/([^" ]+-tags\.tsv)"\)', lib_source)) - {TAGS.name})
    psychology_words = set()
    for filename in tag_files:
        for line in (DATA / filename).read_text(encoding="utf-8").splitlines():
            fields = line.split("\t")
            if len(fields) >= 2 and fields[1].isdigit() and int(fields[1]) & PSYCHOLOGY_BIT:
                psychology_words.add(fields[0].casefold())
    inputs["existing_psychology_words"] = psychology_words
    return inputs


def discover(inputs: dict) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    grouped: dict[tuple[str, str], dict] = {}
    ipa_words = inputs["uk"] | inputs["us"]
    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        expected = ("序號", "英文名稱", "中文名稱", "來源網站")
        if tuple(reader.fieldnames or ()) != expected:
            raise SystemExit(f"Unexpected NAER psychology CSV columns: {reader.fieldnames}")
        for row in reader:
            english = row["英文名稱"].strip().casefold().strip("()")
            if not WORD.fullmatch(english) or english not in ipa_words:
                continue
            noun_glosses = {gloss for gloss, pos in inputs["ecdict"].get(english, ()) if pos == "n."}
            if not noun_glosses:
                continue
            for raw_chinese in VARIANT_SEPARATOR.split(row["中文名稱"].strip()):
                chinese = inputs["converter"].convert(raw_chinese.strip()).strip()
                if not chinese or chinese not in inputs["pinyin"] or chinese not in noun_glosses:
                    continue
                pair = (chinese, english)
                record = grouped.setdefault(pair, {"rows": set(), "source_chinese": set(), "source_urls": set()})
                record["rows"].add(row["序號"].strip())
                record["source_chinese"].add(raw_chinese.strip())
                record["source_urls"].add(row["來源網站"].strip())

    prefilter = []
    for (chinese, english), evidence in sorted(grouped.items()):
        pinyin, frequency = inputs["pinyin"][chinese]
        prefilter.append({
            "english": english,
            "chinese": chinese,
            "source_chinese": " | ".join(sorted(evidence["source_chinese"])),
            "source_records": ",".join(sorted(evidence["rows"], key=int)),
            "source_urls": " | ".join(sorted(evidence["source_urls"])),
            "pinyin": pinyin,
            "pinyin_frequency": str(frequency),
            "ipa_sources": ",".join(name for name, words in (("UK", inputs["uk"]), ("US", inputs["us"])) if english in words),
            "ecdict_exact_noun_glosses": " | ".join(sorted(g for g, pos in inputs["ecdict"].get(english, ()) if pos == "n." and g == chinese)),
            "already_mapped": str((chinese, english) in inputs["pairs"]).lower(),
            "existing_headword": str(english in inputs["words"]).lower(),
            "spare_capacity": str(inputs["extras"].get(chinese, 0) < 8).lower(),
        })
    candidates = [row.copy() for row in prefilter if row["already_mapped"] == "false" and row["spare_capacity"] == "true"]
    return prefilter, candidates


def review(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    decisions = {
        **{pair: ("accept", "") for pair in ACCEPTED_PAIRS},
        **{pair: ("reject", note) for pair, note in REJECTED_PAIRS.items()},
        **{pair: ("defer", note) for pair, note in DEFERRED_PAIRS.items()},
    }
    keys = {(row["chinese"], row["english"]) for row in candidates}
    if keys != set(decisions):
        raise SystemExit(
            "NAER psychology review coverage mismatch: "
            f"unreviewed={ascii(sorted(keys - set(decisions)))}; unexpected={ascii(sorted(set(decisions) - keys))}"
        )
    output = []
    for row in candidates:
        pair = (row["chinese"], row["english"])
        decision, note = decisions[pair]
        if decision == "accept":
            note = (
                "Accepted after review: the official NAER Psychology Terminology record supplies this bilingual "
                "term; the English headword matches the exact local ECDICT noun gloss and has local IPA and a "
                "reachable pinyin key. The source and local evidence support this concise standalone mapping."
            )
        output.append({**row, "decision": decision, "review_note": note})
    return output


def build(prefilter: list[dict[str, str]], candidates: list[dict[str, str]], reviewed: list[dict[str, str]], inputs: dict) -> dict:
    accepted = [row for row in reviewed if row["decision"] == "accept"]
    deferred = [row for row in reviewed if row["decision"] == "defer"]
    rejected = [row for row in reviewed if row["decision"] == "reject"]
    per_key: Counter[str] = Counter()
    expansion_rows = []
    for row in accepted:
        chinese, english = row["chinese"], row["english"]
        if (chinese, english) in inputs["pairs"] or chinese not in inputs["pinyin"]:
            raise SystemExit(f"Accepted NAER psychology mapping is already mapped or unreachable: {chinese} -> {english}")
        if inputs["extras"].get(chinese, 0) + per_key[chinese] >= 8:
            raise SystemExit(f"Accepted NAER psychology mapping exceeds per-key expansion limit: {chinese} -> {english}")
        per_key[chinese] += 1
        expansion_rows.append({"chinese": chinese, "english": english, "pos": "n.", "source": SOURCE})
    expansion_rows.sort(key=lambda row: (row["chinese"], row["english"]))

    exact_by_word: dict[str, list[dict[str, str]]] = {}
    for row in prefilter:
        exact_by_word.setdefault(row["english"], []).append(row)
    tag_rows = [{"english": word, "mask": str(PSYCHOLOGY_BIT), "source": SOURCE} for word in sorted(exact_by_word)]
    tag_review_rows = []
    for word, matching in sorted(exact_by_word.items()):
        tag_review_rows.append({
            "english": word,
            "source_records": ",".join(sorted({number for row in matching for number in row["source_records"].split(",")}, key=int)),
            "source_pairs": " | ".join(f"{row['chinese']} -> {word}" for row in matching),
            "already_psychology_tag": str(word in inputs["existing_psychology_words"]).lower(),
            "decision": "accept",
            "review_note": (
                "Accepted as a psychology-source membership: the headword occurs in the official NAER Psychology "
                "Terminology snapshot and has an exact local noun meaning, IPA, and reachable pinyin. This source "
                "membership does not imply that the word is psychology-specific in every sense."
            ),
        })
    for row in accepted:
        if row["english"] not in exact_by_word:
            raise SystemExit(f"Accepted psychology mapping lacks a psychology source-membership record: {row['english']}")

    outputs = {}
    outputs[PREFILTER.relative_to(DATA).as_posix()] = write_tsv(PREFILTER, PREFILTER_FIELDS, prefilter)
    outputs[CANDIDATES.relative_to(DATA).as_posix()] = write_tsv(CANDIDATES, PREFILTER_FIELDS, candidates)
    outputs[REVIEWED.relative_to(DATA).as_posix()] = write_tsv(REVIEWED, REVIEW_FIELDS, reviewed)
    outputs[TAG_REVIEWED.relative_to(DATA).as_posix()] = write_tsv(TAG_REVIEWED, TAG_FIELDS, tag_review_rows)
    outputs[EXPANSION.relative_to(DATA).as_posix()] = write_tsv(EXPANSION, ("chinese", "english", "pos", "source"), expansion_rows, header=False)
    outputs[TAGS.relative_to(DATA).as_posix()] = write_tsv(TAGS, ("english", "mask", "source"), tag_rows, header=False)

    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as stream:
        source_record_count = sum(1 for _ in csv.DictReader(stream))
    metadata = json.loads(SOURCE_METADATA.read_text(encoding="utf-8-sig"))
    manifest = {
        "batch": "36-naer-psychology-terminology",
        "source": {
            "title": "National Academy for Educational Research - Psychology Terminology",
            "provider": "National Academy for Educational Research",
            "dataset_id": "15167",
            "dataset_url": "https://data.gov.tw/en/datasets/15167",
            "resource_url": metadata["resource_url"],
            "license": "Open Government Data License v1.0",
            "license_url": "https://data.gov.tw/license",
            "portal_updated_at": metadata["portal_updated_at"],
            "snapshot_sha256": SOURCE_SHA256,
            "snapshot_bytes": SOURCE_CSV.stat().st_size,
            "records": source_record_count,
        },
        "filters": {
            "source_scope": "Single-word English entries with exact local ECDICT noun gloss, UK or US IPA, reachable local pinyin key, and local expansion capacity.",
            "candidate_scope": "Every previously unmapped eligible pair receives an explicit accept/reject/defer decision; only reviewed concise standalone mappings enter runtime data.",
            "psychology_tag_scope": "A word receives psychology-source membership only when it occurs in the official NAER Psychology Terminology snapshot and has exact local noun, IPA, and pinyin evidence; membership does not imply every sense is psychology-specific.",
            "traditional_to_simplified": "Traditional Chinese source terms are normalized using OpenCC t2s before matching.",
            "runtime_per_key_cap": 8,
        },
        "counts": {
            "source_records": source_record_count,
            "eligible_exact_pairs": len(prefilter),
            "already_mapped_pairs": sum(row["already_mapped"] == "true" for row in prefilter),
            "capacity_blocked_pairs": sum(row["already_mapped"] == "false" and row["spare_capacity"] == "false" for row in prefilter),
            "new_review_candidates": len(candidates),
            "accepted_mappings": len(accepted),
            "rejected_candidates": len(rejected),
            "deferred_candidates": len(deferred),
            "new_english_headwords": len({row["english"] for row in accepted if row["existing_headword"] == "false"}),
            "psychology_tag_source_memberships": len(tag_rows),
            "new_psychology_tag_memberships": len({row["english"] for row in tag_rows} - inputs["existing_psychology_words"]),
            "reviewed_tag_headwords": len(tag_review_rows),
        },
        "accepted_pairs": [f"{row['chinese']} -> {row['english']} (n.)" for row in accepted],
        "rejected_pairs": [{"pair": f"{row['chinese']} -> {row['english']}", "reason": row["review_note"]} for row in rejected],
        "deferred_pairs": [{"pair": f"{row['chinese']} -> {row['english']}", "reason": row["review_note"]} for row in deferred],
        "source_hashes": {
            SOURCE_CSV.name: SOURCE_SHA256,
            SOURCE_METADATA.name: sha(SOURCE_METADATA.read_bytes()),
            **inputs["runtime_hashes"],
        },
        "base_lexicon_hashes": inputs["hashes"],
        "outputs": {name: sha(payload) for name, payload in outputs.items()},
        "runtime_note": f"Only {len(expansion_rows)} reviewed mappings and {len(tag_rows)} psychology-membership rows enter the once-initialized offline lookup; the {source_record_count:,}-row source CSV is never read while typing.",
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    inputs = load_inputs()
    prefilter, candidates = discover(inputs)
    reviewed = review(candidates)
    manifest = build(prefilter, candidates, reviewed, inputs)
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
