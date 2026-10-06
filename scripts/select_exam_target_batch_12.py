"""Select ECDICT-only exam mappings that add verified, offline pinyin keys.

This tranche uses only exact POS-marked short Chinese glosses from the pinned
ECDICT CSV. Existing Qingjian pinyin keys are preferred; new keys are accepted
only when their reading is independently available from pinned CC-CEDICT or
Rime ICE data. Runtime candidate tags continue to come from the pinned exam
tag index.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
BUILD = ROOT / "build/source-audit"
BASE_TSV = ROOT / "build/runtime-data/base-dict.tsv"
BASE_TSV_SHA256 = "a888bb9b35cc98df29f6b13eb67f78e9ab490d3ff6f8d607f65cf78994c0e460"
OUTPUT = DATA / "exam-target-batch-12-ecdict-expansion.tsv"
REVIEWED = DATA / "batches/12-ecdict-new-pinyin-reviewed.tsv"
OVERLAY = DATA / "pinyin-overlays/exam-target-batch-12.tsv"
MANIFEST = DATA / "exam-target-batch-12-manifest.json"
ECDICT = BUILD / "../vocabulary-research/skywind3000__ECDICT/ecdict.csv"
BATCH_11_FILES = (
    DATA / "exam-target-batch-11-ecdict-expansion.tsv",
    DATA / "exam-target-batch-11-kylebing-expansion.tsv",
    DATA / "exam-target-batch-11-dual-expansion.tsv",
    DATA / "exam-target-batch-11-cow-expansion.tsv",
    DATA / "exam-target-batch-11-koreader-cow-expansion.tsv",
    DATA / "exam-target-batch-11-cc-by-sa-expansion.tsv",
)
BATCH_11_OVERLAY = DATA / "pinyin-overlays/exam-target-batch-11.tsv"
TARGETS = ("cet4", "cet6", "tem4", "tem8", "toefl", "ielts")
BITS = {target: bit for bit, target in enumerate(TARGETS)}
HAN = re.compile(r"[\u3400-\u9fff]{2,6}\Z")
WORD = re.compile(r"[a-z]+(?:[-'][a-z]+)*\Z")
POS_RANK = {"n.": 0, "v.": 1, "adj.": 2, "adv.": 3}
MAX_EXTRA_PER_KEY = 8


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def single_character_pinyin_keys() -> set[str]:
    if not BASE_TSV.is_file() or sha(BASE_TSV) != BASE_TSV_SHA256:
        raise SystemExit("Missing or changed pinned full dictionary TSV; rebuild it from data/dict.qj first")
    keys = set()
    for raw in BASE_TSV.read_text(encoding="utf-8").splitlines():
        fields = raw.split("\t")
        if len(fields) >= 3 and re.fullmatch(r"[\u3400-\u9fff]", fields[0]) and fields[1]:
            keys.add(fields[0])
    return keys


def input_sha(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"Missing pinned batch input: {path}")
    return sha(path)


def load_context() -> dict:
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.path.insert(0, str(ROOT / "build/vocab-tools"))
    import select_exam_target_batch_11 as previous
    from prepare_candidate_batch import source_pos_glosses

    previous.fill_ecdict_pos()
    ctx = previous.load_context()
    return {**ctx, "previous": previous, "source_pos_glosses": source_pos_glosses,
            "single_character_pinyin_keys": single_character_pinyin_keys()}


def batch_11_state(ctx: dict) -> tuple[set[str], collections.Counter, dict[str, tuple[str, str]], list[tuple[str, str, str, str]]]:
    mapped = set(ctx["mapped"])
    extras = collections.Counter({key: len(rows) for key, rows in ctx["extras"].items()})
    rows: list[tuple[str, str, str, str]] = []
    for path in BATCH_11_FILES:
        if not path.is_file():
            raise SystemExit(f"Missing generated batch 11 input: {path}")
        for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            chinese, word, pos, source = raw.split("\t")
            mapped.add(word)
            extras[chinese] += 1
            rows.append((chinese, word, pos, source))
    pinyin_overlay: dict[str, tuple[str, str]] = {}
    for line_number, raw in enumerate(BATCH_11_OVERLAY.read_text(encoding="utf-8").splitlines(), 1):
        fields = raw.split("\t")
        if len(fields) != 4:
            raise SystemExit(f"Invalid batch 11 pinyin overlay row {line_number}")
        chinese, pinyin, frequency, source = fields
        if int(frequency) != 0 or not source:
            raise SystemExit(f"Invalid batch 11 pinyin overlay metadata at row {line_number}")
        pinyin_overlay[chinese] = (pinyin, source)
    return mapped, extras, pinyin_overlay, rows


def load_candidates(ctx: dict) -> tuple[list[dict], collections.Counter, dict]:
    mapped, extras, previous_overlay, previous_rows = batch_11_state(ctx)
    tags, ipa, current_pinyin = ctx["tags"], ctx["ipa"], ctx["current_pinyin"]
    candidate_rows: dict[str, dict[tuple[str, str], dict]] = collections.defaultdict(dict)
    rejected = collections.Counter()
    pinyin_modes = collections.Counter()
    ecdict_record = next(row for row in json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))["input_files"]
                         if row["path"] == "ecdict.csv")
    if sha(ECDICT) != ecdict_record["sha256"]:
        raise SystemExit("Pinned ECDICT source checksum mismatch")

    for row_number, raw in enumerate(csv.DictReader(ECDICT.open(encoding="utf-8-sig", newline="")), 2):
        word = raw.get("word", "").strip().casefold()
        if not WORD.fullmatch(word):
            continue
        if word in mapped:
            continue
        mask = tags.get(word, 0)
        if not mask & 0b111100:
            continue
        if word not in ipa:
            rejected["missing_ipa"] += 1
            continue

        glosses = ctx["source_pos_glosses"](raw.get("translation", ""))
        # One ECDICT row can contain duplicate spellings/POS pairs; retain the
        # first source occurrence so the choice is reproducible and auditable.
        seen: set[tuple[str, str]] = set()
        for gloss_index, (chinese, pos) in enumerate(glosses, 1):
            pair = (chinese, pos)
            if pair in seen:
                continue
            seen.add(pair)
            if not HAN.fullmatch(chinese) or pos not in POS_RANK:
                rejected["invalid_gloss"] += 1
                continue
            if chinese in current_pinyin:
                pinyin = current_pinyin[chinese][0]
                pinyin_source = "Qingjian v0.1.4"
                mode = "existing-key"
                frequency = current_pinyin[chinese][1]
            elif chinese in previous_overlay:
                pinyin, pinyin_source = previous_overlay[chinese]
                mode = "batch-11-overlay"
                frequency = 0
            else:
                resolved = ctx["previous"].resolve_unmapped_pinyin(chinese, ctx)
                if not resolved:
                    rejected["unverified_pinyin"] += 1
                    continue
                pinyin, pinyin_source = resolved
                mode = "new-key"
                frequency = 0
            if not re.fullmatch(r"[a-zv]+(?: [a-zv]+)*", pinyin):
                rejected["invalid_pinyin"] += 1
                continue
            pinyin_modes[mode] += 1
            record = {
                "word": word,
                "chinese": chinese,
                "pos": pos,
                "targets": ",".join(target for target in TARGETS if mask & (1 << BITS[target])),
                "target_mask": mask,
                "pinyin": pinyin,
                "pinyin_source": pinyin_source,
                "frequency": frequency,
                "pinyin_frequency": frequency,
                "pinyin_mode": mode,
                "source_row": row_number,
                "gloss_index": gloss_index,
            }
            old = candidate_rows[word].get(pair)
            if old is None or gloss_index < old["gloss_index"]:
                candidate_rows[word][pair] = record

    # Prefer an existing normal Qingjian input key. Among equally usable
    # senses preserve the order in the ECDICT POS-marked definition.
    def row_order(row: dict) -> tuple:
        mode_rank = {"existing-key": 0, "batch-11-overlay": 1, "new-key": 2}[row["pinyin_mode"]]
        return (mode_rank, row["gloss_index"], POS_RANK[row["pos"]],
                -int(row["frequency"]), row["chinese"])

    ordered_words = sorted(candidate_rows, key=lambda word: (
        -sum(bool(ctx["tags"][word] & (1 << BITS[target])) for target in TARGETS[2:]),
        word,
    ))
    selected: list[dict] = []
    used_words = set()
    for word in ordered_words:
        choices = sorted(candidate_rows[word].values(), key=row_order)
        for row in choices:
            if extras[row["chinese"]] >= MAX_EXTRA_PER_KEY:
                rejected["per_chinese_key_capacity"] += 1
                continue
            source = "ECDICT MIT"
            confidence = {
                "existing-key": "exact ECDICT POS-marked gloss; existing Qingjian pinyin key",
                "batch-11-overlay": "exact ECDICT POS-marked gloss; verified batch 11 pinyin key",
                "new-key": "exact ECDICT POS-marked gloss; independently sourced pinyin key",
            }[row["pinyin_mode"]]
            row.update({
                "source": source,
                "source_reference": f"ecdict.csv row {row['source_row']}; POS gloss {row['gloss_index']}",
                "confidence": confidence,
                "evidence": f"Exact POS-marked ECDICT short gloss; pinyin: {row['pinyin_source']}",
                "priority": row_order(row),
            })
            selected.append(row)
            used_words.add(word)
            extras[row["chinese"]] += 1
            break
        else:
            rejected["headword_without_key_capacity"] += 1

    selected.sort(key=lambda row: (row["chinese"], row["word"], row["pos"]))
    return selected, rejected, {
        "candidate_headwords_with_verified_key": len(candidate_rows),
        "selected_headwords": len(used_words),
        "pinyin_modes_seen": dict(sorted(pinyin_modes.items())),
        "previous_mapping_rows": previous_rows,
        "previous_overlay": previous_overlay,
        "previous_mapped": mapped,
        "previous_extras": collections.Counter({key: len(rows) for key, rows in ctx["extras"].items()}),
    }


def render(rows: list[dict], ctx: dict, state: dict, rejected: collections.Counter) -> tuple[str, str, str, dict]:
    review_headers = ("word", "chinese", "pos", "targets", "source", "source_reference",
                     "pinyin", "pinyin_source", "pinyin_frequency", "confidence", "evidence")
    review = "\t".join(review_headers) + "\n" + "".join(
        "\t".join(str(row[key]).replace("\t", " ").replace("\n", r"\n")
                  for key in review_headers) + "\n" for row in rows)
    expansion = "".join(f"{row['chinese']}\t{row['word']}\t{row['pos']}\tECDICT MIT\n" for row in rows)
    existing_pinyin = set(ctx["current_pinyin"]) | set(state["previous_overlay"])
    overlay_rows: dict[str, tuple[str, str]] = {}
    for row in rows:
        chinese = row["chinese"]
        if chinese in existing_pinyin:
            continue
        value = (row["pinyin"], row["pinyin_source"])
        old = overlay_rows.get(chinese)
        if old and old[0] != value[0]:
            raise SystemExit(f"Selected ECDICT rows disagree on pinyin for {chinese}")
        overlay_rows[chinese] = value
    overlay = "".join(f"{chinese}\t{pinyin}\t0\t{source}\n"
                      for chinese, (pinyin, source) in sorted(overlay_rows.items()))

    current_words = set(state["previous_mapped"])
    added_words = {row["word"] for row in rows}
    current_pinyin = dict(ctx["current_pinyin"])
    current_pinyin.update({chinese: (pinyin, 0) for chinese, (pinyin, _source) in state["previous_overlay"].items()})
    after_pinyin = dict(current_pinyin)
    after_pinyin.update({chinese: (pinyin, 0) for chinese, (pinyin, _source) in overlay_rows.items()})

    before_reachable = {word for chinese, senses in ctx["base"].items() if chinese in current_pinyin
                        for word, _pos in senses}
    single_keys = ctx["single_character_pinyin_keys"]
    before_reachable.update(word for chinese, senses in ctx["base"].items()
                            if chinese in single_keys for word, _pos in senses)
    runtime_rows: list[tuple[str, str, str, str]] = []
    for filename in ctx["runtime_files"]:
        if filename in ctx["previous"].GENERATED_NAMES:
            continue
        path = DATA / filename
        if path.is_file():
            for raw in path.read_text(encoding="utf-8").splitlines():
                runtime_rows.append(tuple(raw.split("\t")))
    runtime_rows.extend(state["previous_mapping_rows"])
    before_reachable.update(word for chinese, word, _pos, _source in runtime_rows
                            if chinese in set(current_pinyin) | single_keys)
    after_reachable = set(before_reachable)
    # New keys can also expose pre-existing base-dictionary senses that share
    # their Chinese surface, even when those senses were not selected in this
    # expansion batch.
    after_keys = set(after_pinyin) | single_keys
    after_reachable.update(word for chinese, senses in ctx["base"].items()
                           if chinese in after_keys for word, _pos in senses)
    # A new pinyin key also unlocks any existing runtime glosses that use the
    # same Chinese surface, not only the selected ECDICT row that introduced
    # the key. Count those newly reachable senses in the audited coverage.
    after_reachable.update(word for chinese, word, _pos, _source in runtime_rows
                           if chinese in after_keys)
    after_reachable.update(row["word"] for row in rows
                           if row["chinese"] in after_pinyin)

    tags, ipa = ctx["tags"], ctx["ipa"]
    coverage_before = ctx["coverage"](tags, current_words, ipa)
    coverage_after = ctx["coverage"](tags, current_words | added_words, ipa)
    reachable_before = ctx["coverage"](tags, before_reachable, ipa)
    reachable_after = ctx["coverage"](tags, after_reachable, ipa)
    by_target = {target: len({row["word"] for row in rows if tags[row["word"]] & (1 << BITS[target])})
                 for target in TARGETS}
    modes_selected = collections.Counter(row["pinyin_mode"] for row in rows)
    inputs = {
        "ecdict_sha256": input_sha(ECDICT),
        "full_base_dictionary_tsv_sha256": sha(BASE_TSV),
        "english_tag_manifest_sha256": sha(DATA / "manifest.json"),
        "batch_11_manifest_sha256": sha(DATA / "exam-target-batch-11-manifest.json"),
        "batch_11_pinyin_overlay_sha256": input_sha(BATCH_11_OVERLAY),
        "cc_cedict_sha256": "8172061b2a647dd8a179788830ef233944baee479bc7018f111064ad16d8f46f",
        "rime_ice_commit": "da1fbe602e38f26db846fa10120ee64c2b0324c0",
        "rime_base_sha256": input_sha(BUILD / "rime-ice/da1fbe602e38f26db846fa10120ee64c2b0324c0/cn_dicts/base.dict.yaml"),
        "rime_ext_sha256": input_sha(BUILD / "rime-ice/da1fbe602e38f26db846fa10120ee64c2b0324c0/cn_dicts/ext.dict.yaml"),
    }
    for path in BATCH_11_FILES:
        inputs[path.name + "_sha256"] = input_sha(path)
    manifest = {
        "batch": "12-ecdict-exam-terms-with-pinyin-v1",
        "selected_pairs": len(rows),
        "selected_unique_headwords": len({row["word"] for row in rows}),
        "selected_new_pinyin_keys": len(overlay_rows),
        "selected_by_target": by_target,
        "selected_by_pinyin_mode": dict(sorted(modes_selected.items())),
        "candidate_headwords_with_verified_key": state["candidate_headwords_with_verified_key"],
        "coverage_before": coverage_before,
        "coverage_after": coverage_after,
        "pinyin_reachable_coverage_before": reachable_before,
        "pinyin_reachable_coverage_after": reachable_after,
        "rejected_or_unselected": dict(sorted(rejected.items())),
        "selection": {
            "source": "Pinned ECDICT MIT English-to-Chinese dictionary; exact complete 2-6 Han-character glosses with explicit POS.",
            "target_tags": ["tem4", "tem8", "toefl", "ielts"],
            "ipa_required": True,
            "pinyin": "Existing pinned Qingjian key, previously verified batch 11 key, or a single-source reading from pinned CC-CEDICT/Rime ICE when the other source has no entry; when both sources contain the key, their normalized readings must agree.",
            "priority": "Existing Qingjian keys first, then batch 11 verified keys, then new keys with independent pinned reading evidence. New pinyin entries have frequency zero.",
            "one_mapping_per_headword": True,
            "max_extra_rows_per_chinese_key": MAX_EXTRA_PER_KEY,
            "candidate_order": "No existing Qingjian pinyin candidate is reordered; new rows append at frequency zero.",
            "review_limit": "Automated deterministic source and POS filtering, not a claim of human review for every row.",
        },
        "inputs": inputs,
        "outputs": {
            "reviewed": {"sha256": hashlib.sha256(review.encode()).hexdigest(), "rows": len(rows)},
            "pinyin_overlay": {"sha256": hashlib.sha256(overlay.encode()).hexdigest(), "rows": len(overlay_rows)},
            "exam-target-batch-12-ecdict-expansion.tsv": {
                "sha256": hashlib.sha256(expansion.encode()).hexdigest(), "rows": len(rows)},
        },
        "licenses": {
            "expansion": "ECDICT MIT; see vocabulary/data/ECDICT-LICENSE",
            "pinyin_overlay": "Per-row source labels distinguish CC-CEDICT CC BY-SA 4.0 and Rime ICE GPL-3.0; see NOTICE.txt and pinned source manifests.",
        },
        "limitations": "Exam coverage uses fixed community lists rather than official complete syllabi. Mapping coverage means a whole Chinese-to-English exact gloss is present. Pinyin reachability means the full reading exists; the headword may still be below the first visible candidate page.",
    }
    return review, overlay, expansion, manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--select", action="store_true", help="write the selected mapping and overlay")
    mode.add_argument("--check", action="store_true", help="verify deterministic outputs")
    args = parser.parse_args()
    ctx = load_context()
    rows, rejected, state = load_candidates(ctx)
    review, overlay, expansion, manifest = render(rows, ctx, state, rejected)
    payloads = {
        REVIEWED: review,
        OVERLAY: overlay,
        OUTPUT: expansion,
        MANIFEST: json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    }
    if args.check:
        changed = [str(path.relative_to(ROOT)) for path, payload in payloads.items()
                   if not path.is_file() or path.read_text(encoding="utf-8") != payload]
        if changed:
            raise SystemExit("Batch 12 outputs differ: " + ", ".join(changed))
    else:
        for path, payload in payloads.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload, encoding="utf-8", newline="\n")
    print(json.dumps({
        "selected_pairs": len(rows),
        "selected_by_target": manifest["selected_by_target"],
        "new_pinyin_keys": manifest["selected_new_pinyin_keys"],
        "selected_by_pinyin_mode": manifest["selected_by_pinyin_mode"],
        "coverage_after": {target: manifest["coverage_after"][target]["percent"] for target in TARGETS},
        "pinyin_reachable_after": {target: manifest["pinyin_reachable_coverage_after"][target]["percent"] for target in TARGETS},
        "rejected": dict(sorted(rejected.items())),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
