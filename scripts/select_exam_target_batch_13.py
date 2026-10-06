"""Add verified pinyin keys for already-mapped exam vocabulary.

Batch 13 does not invent English-Chinese translations. It finds target-word
glosses already present in the pinned Qingjian/runtime vocabulary whose
Chinese surface has no pinyin dictionary entry, then adds only enough
frequency-zero pinyin keys to bring TOEFL input reachability to 90%.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
OUTPUT = DATA / "pinyin-overlays/exam-target-batch-13.tsv"
REVIEWED = DATA / "batches/13-exam-pinyin-reachability.tsv"
MANIFEST = DATA / "exam-target-batch-13-manifest.json"
TARGETS = ("cet4", "cet6", "tem4", "tem8", "toefl", "ielts")
BITS = {target: bit for bit, target in enumerate(TARGETS)}
HAN = re.compile(r"[\u3400-\u9fff]{2,6}\Z")
TOEFL_GOAL = 0.90


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pinyin_for_key(chinese: str, context: dict):
    resolved = context["previous"].resolve_unmapped_pinyin(chinese, context)
    if resolved:
        reading, source = resolved
        return reading, source, "cedict-rime", "single independently listed phrase reading"
    return None


def runtime_pairs(context: dict, batch11_rows: list[tuple[str, str, str, str]], batch12_rows: list[dict]):
    pairs: dict[str, set[str]] = collections.defaultdict(set)
    pair_sources: dict[tuple[str, str], str] = {}
    for chinese, senses in context["base"].items():
        if not HAN.fullmatch(chinese):
            continue
        for word, _pos in senses:
            if context["tags"].get(word, 0):
                pairs[chinese].add(word)
                pair_sources.setdefault((chinese, word), "Qingjian v0.1.4 glossary")
    for filename in context["runtime_files"]:
        path = DATA / filename
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            fields = raw.split("\t")
            if len(fields) < 4:
                continue
            chinese, word, _pos, source = fields[:4]
            if not HAN.fullmatch(chinese):
                continue
            if context["tags"].get(word, 0):
                pairs[chinese].add(word)
                pair_sources.setdefault((chinese, word), source)
    for chinese, word, _pos, source in batch11_rows:
        if not HAN.fullmatch(chinese):
            continue
        pairs[chinese].add(word)
        pair_sources[(chinese, word)] = source
    for row in batch12_rows:
        if not HAN.fullmatch(row["chinese"]):
            continue
        pairs[row["chinese"]].add(row["word"])
        pair_sources[(row["chinese"], row["word"])] = row["source"]
    return pairs, pair_sources


def baseline(context: dict, batch12_rows: list[dict], batch12_state: dict, batch12_manifest: dict):
    # Reproduce batch 12's exact after-pinyin reachability computation. Some
    # selected expansion rows share a Chinese key that was never admitted to
    # the runtime pinyin map; including every row's surface would overstate the
    # prior baseline.
    current_pinyin = dict(context["current_pinyin"])
    current_pinyin.update({
        chinese: (pinyin, 0)
        for chinese, (pinyin, _source) in batch12_state["previous_overlay"].items()
    })
    previous_keys = set(current_pinyin)
    batch12_overlay: dict[str, tuple[str, str]] = {}
    for row in batch12_rows:
        chinese = row["chinese"]
        if chinese in previous_keys:
            continue
        value = (row["pinyin"], row["pinyin_source"])
        old = batch12_overlay.get(chinese)
        if old and old[0] != value[0]:
            raise SystemExit(f"Batch 12 pinyin overlay disagreement for {chinese}")
        batch12_overlay[chinese] = value
    current_pinyin.update({chinese: (pinyin, 0) for chinese, (pinyin, _source) in batch12_overlay.items()})
    # The C ABI exposes genuine one-character candidates from the pinned
    # dictionary too; the research exporter intentionally omits them when
    # finding new multi-character expansion keys.
    current_keys = set(current_pinyin) | context["single_character_pinyin_keys"]

    reachable = {word for chinese, senses in context["base"].items() if chinese in current_keys
                 for word, _pos in senses}
    current_runtime_rows = []
    for filename in context["runtime_files"]:
        if filename in context["previous"].GENERATED_NAMES:
            continue
        path = DATA / filename
        if path.is_file():
            current_runtime_rows.extend(raw.split("\t") for raw in path.read_text(encoding="utf-8").splitlines())
    reachable.update(row[1] for row in current_runtime_rows if row[0] in current_keys and len(row) > 1)
    reachable.update(
        word for chinese, word, _pos, _source in batch12_state["previous_mapping_rows"]
        if chinese in current_keys
    )
    reachable.update(row["word"] for row in batch12_rows if row["chinese"] in current_keys)
    before = context["coverage"](context["tags"], reachable, context["ipa"])
    if before != batch12_manifest["pinyin_reachable_coverage_after"]:
        raise SystemExit(
            "Batch 12 pinyin reachability baseline mismatch; "
            f"calculated TOEFL={before['toefl']} vs saved={batch12_manifest['pinyin_reachable_coverage_after']['toefl']}"
        )
    return current_keys, reachable, before


def select(context: dict, pairs: dict[str, set[str]], pair_sources: dict[tuple[str, str], str],
           known_keys: set[str], reachable: set[str]):
    tags = context["tags"]
    toefl_bit = 1 << BITS["toefl"]
    toefl_words = {word for word, mask in tags.items() if mask & toefl_bit}
    current_toefl = len(toefl_words & reachable)
    required_total = math.ceil(context["coverage"](tags, reachable, context["ipa"])["toefl"]["total"] * TOEFL_GOAL)
    required_gain = max(0, required_total - current_toefl)

    candidates = {}
    skipped = collections.Counter()
    for chinese, words in pairs.items():
        if chinese in known_keys:
            continue
        missing = words - reachable
        if not (missing & toefl_words):
            continue
        pinyin = pinyin_for_key(chinese, context)
        if not pinyin:
            skipped["no single verified pinyin source"] += 1
            continue
        reading, source, mode, confidence = pinyin
        candidates[chinese] = {
            "chinese": chinese, "pinyin": reading, "source": source,
            "mode": mode, "confidence": confidence,
            "words": missing,
            "toefl_words": missing & toefl_words,
            "ipa_toefl_words": missing & toefl_words & context["ipa"],
            "quality": {"cedict-rime": 2}[mode],
        }

    selected = []
    covered = set()
    while len(covered & toefl_words) < required_gain:
        best = None
        best_score = None
        for chinese, item in candidates.items():
            remaining = item["words"] - covered
            toefl_gain = len(remaining & toefl_words)
            if not toefl_gain:
                continue
            score = (
                len(remaining & item["ipa_toefl_words"]), toefl_gain,
                len(remaining), item["quality"], -len(chinese), chinese,
            )
            if best_score is None or score > best_score:
                best, best_score = chinese, score
        if best is None:
            raise SystemExit(
                f"Verified pinyin sources can only reach {current_toefl + len(covered & toefl_words)} "
                f"of {required_total} TOEFL headwords"
            )
        item = candidates.pop(best)
        selected.append(item)
        covered.update(item["words"])
    selected.sort(key=lambda item: item["chinese"])
    verified_count = len(candidates) + len(selected)
    return selected, skipped, required_total, verified_count


def render(context: dict, batch12_rows: list[dict], batch12_state: dict, batch12_manifest: dict,
           pairs: dict[str, set[str]], pair_sources: dict[tuple[str, str], str],
           selected: list[dict], skipped: collections.Counter, required_total: int,
           verified_count: int):
    known_keys, reachable, before = baseline(context, batch12_rows, batch12_state, batch12_manifest)
    overlay = "".join(
        f"{row['chinese']}\t{row['pinyin']}\t0\t{row['source']}\n" for row in selected
    )
    selected_words = set(reachable)
    for row in selected:
        selected_words.update(row["words"])
    after = context["coverage"](context["tags"], selected_words, context["ipa"])
    if after["toefl"]["mapped"] < required_total:
        raise SystemExit("Batch 13 output does not reach the requested TOEFL pinyin coverage")

    review_header = ("chinese", "pinyin", "frequency", "source", "mode", "confidence",
                     "example_toefl_headword", "example_translation_source")
    review_rows = []
    source_counts = collections.Counter()
    mode_counts = collections.Counter()
    for row in selected:
        example = min(row["toefl_words"])
        review_rows.append({
            "chinese": row["chinese"], "pinyin": row["pinyin"], "frequency": 0,
            "source": row["source"], "mode": row["mode"], "confidence": row["confidence"],
            "example_toefl_headword": example,
            "example_translation_source": pair_sources.get((row["chinese"], example), "existing runtime glossary"),
        })
        source_counts[row["source"]] += 1
        mode_counts[row["mode"]] += 1
    review = "\t".join(review_header) + "\n" + "".join(
        "\t".join(str(row[key]).replace("\t", " ").replace("\n", " ") for key in review_header) + "\n"
        for row in review_rows
    )

    all_words = set(reachable)
    for row in selected:
        all_words.update(row["words"])
    toefl_total = before["toefl"]["total"]
    manifest = {
        "batch": "13-pinyin-reachability-target-v1",
        "purpose": "Make already-present English exam senses reachable by pinyin without adding or reordering Chinese translations.",
        "target_goal": {"toefl_pinyin_reachable_percent": TOEFL_GOAL * 100,
                        "minimum_reachable_headwords": required_total},
        "selected_new_pinyin_keys": len(selected),
        "selected_runtime_pinyin_entries": len(selected),
        "selected_by_source": dict(sorted(source_counts.items())),
        "selected_by_mode": dict(sorted(mode_counts.items())),
        "existing_pinyin_entries": len(context["current_pinyin"]),
        "candidate_keys_with_verified_reading": verified_count,
        "verified_keys_not_needed_for_90_percent_goal": verified_count - len(selected),
        "candidate_keys_scanned": len(pairs),
        "pinyin_reachable_before": before,
        "pinyin_reachable_after": after,
        "mapping_coverage_changed": False,
        "newly_reachable_exam_headwords": {
            target: after[target]["mapped"] - before[target]["mapped"] for target in TARGETS
        },
        "toefl_headwords_reachable_after": after["toefl"]["mapped"],
        "toefl_headword_total": toefl_total,
        "unselected": dict(sorted(skipped.items())),
        "selection": {
            "only_existing_glosses": True,
            "no_new_english_chinese_translation_pairs": True,
            "new_key_frequency": 0,
            "candidate_order": "Existing input candidates remain byte-for-byte in their original relative order; new keys use frequency zero.",
            "reading_sources": [
                "CC-CEDICT and Rime ICE exact phrase readings when their pinned readings resolve uniquely",
            ],
            "priority": "Greedy deterministic key selection until TOEFL pinyin reachability reaches at least 90%; prefer IPA-backed TOEFL senses, then unlock more exam senses, then higher-confidence pinyin sources.",
            "limitations": "Reachable means the complete pinyin key is present; a low-frequency candidate can still appear below the first visible page. Coverage uses fixed community word lists, not an official complete syllabus.",
        },
        "inputs": {
            "base_dictionary_sha256": "3e33b16a84df555e6f16d52ac8ab3c2c6b6f1f71734e69463861fd5abd9c19dc",
            "batch_11_manifest_sha256": sha(DATA / "exam-target-batch-11-manifest.json"),
            "batch_12_manifest_sha256": sha(DATA / "exam-target-batch-12-manifest.json"),
            "pinyin_candidates_sha256": sha(ROOT / "build/pinyin-candidates.tsv"),
            "full_base_dictionary_tsv_sha256": sha(ROOT / "build/runtime-data/base-dict.tsv"),
            "runtime_files": {name: sha(DATA / name) for name in context["runtime_files"] if (DATA / name).is_file()},
        },
        "outputs": {
            REVIEWED.name: {"sha256": hashlib.sha256(review.encode()).hexdigest(), "rows": len(selected)},
            OUTPUT.name: {"sha256": hashlib.sha256(overlay.encode()).hexdigest(), "rows": len(selected)},
        },
        "licenses": {
            "CC-CEDICT and Rime ICE rows": "Row-level attribution retained in the overlay; see NOTICE.txt.",
        },
    }
    return review, overlay, manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--select", action="store_true", help="write deterministic batch 13 outputs")
    mode.add_argument("--check", action="store_true", help="verify saved outputs against pinned inputs")
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT / "scripts"))
    import select_exam_target_batch_12 as batch12

    context = batch12.load_context()
    batch11 = batch12.batch_11_state(context)
    rows12, rejected12, state12 = batch12.load_candidates(context)
    _review12, _overlay12, _expansion12, manifest12 = batch12.render(rows12, context, state12, rejected12)
    known_keys, reachable, _before = baseline(context, rows12, state12, manifest12)
    pairs, pair_sources = runtime_pairs(context, batch11[3], rows12)
    selected, skipped, required_total, verified_count = select(
        context, pairs, pair_sources, known_keys, reachable
    )
    review, overlay, manifest = render(
        context, rows12, state12, manifest12, pairs, pair_sources, selected, skipped, required_total,
        verified_count,
    )
    outputs = {
        REVIEWED: review,
        OUTPUT: overlay,
        MANIFEST: json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    }
    if args.check:
        changed = [str(path.relative_to(ROOT)) for path, payload in outputs.items()
                   if not path.is_file() or path.read_text(encoding="utf-8") != payload]
        if changed:
            raise SystemExit("Batch 13 outputs differ: " + ", ".join(changed))
    else:
        for path, payload in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload, encoding="utf-8", newline="\n")
    print(json.dumps({
        "selected_new_pinyin_keys": manifest["selected_new_pinyin_keys"],
        "pinyin_reachable_after": {target: manifest["pinyin_reachable_after"][target]["percent"] for target in TARGETS},
        "toefl_headwords_reachable_after": manifest["toefl_headwords_reachable_after"],
        "toefl_headword_total": manifest["toefl_headword_total"],
        "sources": manifest["selected_by_source"],
        "modes": manifest["selected_by_mode"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
