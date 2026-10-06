"""Create a review-only queue for missing TEM4/TEM8/TOEFL/IELTS mappings.

Every row is an exact short ECDICT Chinese gloss on an existing Qingjian
pinyin candidate key and has bundled IPA. KyleBing agreement and WordNet
relation to an existing glossary sense are additional confidence signals,
not mandatory candidate filters. The script never edits shipped data.
"""
from __future__ import annotations

import collections
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from prepare_cet_batch import load_base
from prepare_candidate_batch import KYLE_POS, kyle_glosses, parse_pinyin_candidates, sha, source_pos_glosses
from wordnet_guard import WordNetGuard
from exam_targets import load_exam_tags, RUNTIME_EXPANSIONS

DATA = ROOT / "vocabulary/data"
OUT = ROOT / "build/source-audit/exam-targets"
TARGETS = ("tem4", "tem8", "toefl", "ielts")
TARGET_FILES = {
    "tem4": "专四.jsonl",
    "tem8": "专八.jsonl",
    "toefl": "托福.jsonl",
    "ielts": "雅思.jsonl",
}
TARGET_BITS = {target: bit for bit, target in enumerate(("cet4", "cet6", "tem4", "tem8", "toefl", "ielts"))}
RUNTIME_FILES = RUNTIME_EXPANSIONS


def load_ipa() -> set[str]:
    return {
        line.split("\t", 1)[0].strip().casefold()
        for name in ("en_UK.txt", "en_US.txt")
        for line in (ROOT / "pronunciation/source" / name).read_text(encoding="utf-8").splitlines()
        if "\t" in line
    }


def main() -> None:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    records = {row["path"]: row for row in manifest["input_files"]}
    tags_path = DATA / "english-tags.tsv"
    if sha(tags_path) != manifest["sha256"]:
        raise SystemExit("Pinned exam tag index checksum mismatch")

    tags = load_exam_tags(DATA)
    base = load_base(ROOT / "build/expansion-base.tsv")
    pinyin = parse_pinyin_candidates(ROOT / "build/pinyin-candidates.tsv")
    ipa = load_ipa()

    existing_words = {word for senses in base.values() for word, _ in senses}
    key_rows: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    for filename in RUNTIME_FILES:
        for line in (DATA / filename).read_text(encoding="utf-8").splitlines():
            chinese, english, pos, _source = line.split("\t")
            existing_words.add(english)
            key_rows[chinese].append((english, pos))

    # Do not add more than eight expansion rows to any one Chinese candidate.
    current_extra_count = collections.Counter({key: len(rows) for key, rows in key_rows.items()})
    missing_by_target = {
        target: {word for word, mask in tags.items()
                 if mask & (1 << TARGET_BITS[target]) and word not in existing_words}
        for target in TARGETS
    }
    missing_union = set().union(*missing_by_target.values())

    kyle_root = ROOT / "build/vocabulary-research/KyleBing__english-vocabulary/full_line_jsonl/simple/正序"
    kyle_pairs: dict[tuple[str, str, str], set[str]] = collections.defaultdict(set)
    for target, filename in TARGET_FILES.items():
        record_path = "full_line_jsonl/simple/正序/" + filename
        record = records.get(record_path)
        if record is None:
            raise SystemExit("Missing pinned KyleBing input record: " + record_path)
        source = kyle_root / filename
        if not source.is_file() or sha(source) != record["sha256"]:
            raise SystemExit("Pinned KyleBing checksum mismatch: " + record_path)
        with source.open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                word = str(row.get("word", "")).strip().casefold()
                if word not in missing_union:
                    continue
                for meaning in row.get("translations", []):
                    pos = KYLE_POS.get(str(meaning.get("type", "")).strip().lower())
                    if not pos:
                        continue
                    for chinese in kyle_glosses(meaning.get("translation", "")):
                        kyle_pairs[(word, chinese, pos)].add(target)

    ecdict_record = records.get("ecdict.csv")
    if not ecdict_record:
        raise SystemExit("Missing pinned ECDICT input record")
    ecdict_path = ROOT / "build/vocabulary-research/skywind3000__ECDICT/ecdict.csv"
    if not ecdict_path.is_file() or sha(ecdict_path) != ecdict_record["sha256"]:
        raise SystemExit("Pinned ECDICT checksum mismatch")

    guard = WordNetGuard()
    candidates: dict[tuple[str, str, str], dict[str, str]] = {}
    ecdict_pairs: set[tuple[str, str, str]] = set()
    ecdict_translation_by_word: dict[str, str] = {}
    with ecdict_path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            word = row["word"].strip().casefold()
            if word not in missing_union or word not in ipa:
                continue
            ecdict_translation_by_word[word] = row.get("translation", "").replace("\n", r"\n")
            try:
                rank = int(row.get("frq") or row.get("bnc") or 999999) or 999999
            except ValueError:
                rank = 999999
            for chinese, pos in source_pos_glosses(row.get("translation", "")):
                pair = (word, chinese, pos)
                ecdict_pairs.add(pair)
                kyle_sources = sorted(kyle_pairs.get(pair, ()))
                if chinese not in pinyin:
                    continue
                base_pos = {base_pos for _, base_pos in base.get(chinese, [])}
                pos_match = pos in base_pos
                wordnet_related = bool(
                    chinese in base and pos_match and guard.synsets(word, pos)
                    and guard.related(word, pos, base[chinese])
                )
                if wordnet_related and kyle_sources:
                    tier = "dual-source-wordnet"
                elif kyle_sources:
                    tier = "dual-source"
                else:
                    tier = "ecdict-only"
                mask = tags[word]
                matched_targets = [target for target in TARGETS
                                   if mask & (1 << TARGET_BITS[target])]
                key = (word, chinese, pos)
                candidates[key] = {
                    "word": word,
                    "chinese": chinese,
                    "pos": pos,
                    "confidence_tier": tier,
                    "targets": ",".join(matched_targets),
                    "kyle_sources": ",".join(kyle_sources),
                    "wordnet_related_to_base_sense": "yes" if wordnet_related else "no",
                    "packed_gloss_key": "yes" if chinese in base else "no",
                    "base_pos_match": "yes" if pos_match else ("no" if chinese in base else "new-key"),
                    "key_capacity_available": "yes" if current_extra_count[chinese] < 8 else "no",
                    "pinyin": pinyin[chinese][0],
                    "pinyin_frequency": str(pinyin[chinese][1]),
                    "ecdict_frequency_rank": str(rank),
                    "base_senses": " | ".join(f"{sense} [{sense_pos}]" for sense, sense_pos in base.get(chinese, [])),
                    "ecdict_translation": row.get("translation", "").replace("\n", r"\n"),
                    "ecdict_exact_pos_gloss": "yes",
                    "kyle_exact_pos_gloss": "yes" if kyle_sources else "no",
                    "ipa": "yes",
                }

    # Some target lists contain an exact, inputtable translation absent from
    # ECDICT's short glosses. Keep those visible as a separate single-source tier.
    for (word, chinese, pos), sources in sorted(kyle_pairs.items()):
        if (word, chinese, pos) in ecdict_pairs or chinese not in pinyin or word not in ipa:
            continue
        base_pos = {base_pos for _, base_pos in base.get(chinese, [])}
        pos_match = pos in base_pos
        wordnet_related = bool(
            chinese in base and pos_match and guard.synsets(word, pos)
            and guard.related(word, pos, base[chinese])
        )
        mask = tags[word]
        matched_targets = [target for target in TARGETS if mask & (1 << TARGET_BITS[target])]
        candidates[(word, chinese, pos)] = {
            "word": word,
            "chinese": chinese,
            "pos": pos,
            "confidence_tier": "kyle-only",
            "targets": ",".join(matched_targets),
            "kyle_sources": ",".join(sorted(sources)),
            "ecdict_exact_pos_gloss": "no",
            "kyle_exact_pos_gloss": "yes",
            "wordnet_related_to_base_sense": "yes" if wordnet_related else "no",
            "packed_gloss_key": "yes" if chinese in base else "no",
            "base_pos_match": "yes" if pos_match else ("no" if chinese in base else "new-key"),
            "key_capacity_available": "yes" if current_extra_count[chinese] < 8 else "no",
            "pinyin": pinyin[chinese][0],
            "pinyin_frequency": str(pinyin[chinese][1]),
            "ecdict_frequency_rank": "999999",
            "base_senses": " | ".join(f"{sense} [{sense_pos}]" for sense, sense_pos in base.get(chinese, [])),
            "ecdict_translation": ecdict_translation_by_word.get(word, ""),
            "ipa": "yes",
        }

    headers = (
        "word", "chinese", "pos", "confidence_tier", "targets", "kyle_sources",
        "ecdict_exact_pos_gloss", "kyle_exact_pos_gloss", "wordnet_related_to_base_sense", "packed_gloss_key",
        "base_pos_match", "key_capacity_available", "pinyin", "pinyin_frequency",
        "ecdict_frequency_rank", "base_senses", "ecdict_translation", "ipa",
    )
    ordered = sorted(candidates.values(), key=lambda item: (
        {"dual-source-wordnet": 0, "dual-source": 1, "ecdict-only": 2, "kyle-only": 3}[item["confidence_tier"]],
        -len(item["targets"].split(",")), -int(item["pinyin_frequency"]),
        int(item["ecdict_frequency_rank"]), item["word"], item["chinese"],
    ))
    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / "candidate-review.tsv"
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(ordered)

    summary = {
        "scope": list(TARGETS),
        "inputs": {
            "english_tags_sha256": sha(tags_path),
            "ecdict_sha256": sha(ecdict_path),
            "pinyin_candidates_sha256": sha(ROOT / "build/pinyin-candidates.tsv"),
            "kylebing_files": {
                target: records["full_line_jsonl/simple/正序/" + filename]["sha256"]
                for target, filename in TARGET_FILES.items()
            },
        },
        "missing_headwords_before_review": {
            target: len(missing_by_target[target]) for target in TARGETS
        },
        "candidate_pairs_after_conservative_filters": len(ordered),
        "candidate_headwords": len({row["word"] for row in ordered}),
        "candidate_headwords_by_target": {
            target: len({row["word"] for row in ordered if target in row["targets"].split(",")})
            for target in TARGETS
        },
        "candidate_pair_rows_by_target": {
            target: sum(target in row["targets"].split(",") for row in ordered)
            for target in TARGETS
        },
        "candidate_headwords_by_target_and_tier": {
            target: {
                tier: len({row["word"] for row in ordered
                           if target in row["targets"].split(",") and row["confidence_tier"] == tier})
                for tier in ("dual-source-wordnet", "dual-source", "ecdict-only", "kyle-only")
            }
            for target in TARGETS
        },
        "candidate_headwords_by_target_with_capacity": {
            target: len({row["word"] for row in ordered
                         if target in row["targets"].split(",") and row["key_capacity_available"] == "yes"})
            for target in TARGETS
        },
        "output_sha256": sha(output),
        "selection_rule": "Review-only. Requires an exact complete 2–6 Han-character Chinese gloss from pinned ECDICT or the pinned target-specific KyleBing exam list, an exact current Qingjian pinyin candidate key, target exam membership, and bundled IPA. Exact agreement across ECDICT and KyleBing, an existing packed glossary key, compatible POS, WordNet relation, and key capacity are recorded as quality signals. New keys work in the runtime expansion translator but need especially careful manual review.",
        "caveat": "No candidate is automatically adopted. Review the English sense, register, Chinese gloss, POS, and key capacity before selecting it for the runtime data.",
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
