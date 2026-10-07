"""Build reviewed CET4/CET6 mappings from a pinned CC BY-SA word list."""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
SOURCE_COMMIT = "7d89f3697abf26e305fe2627f181b692c2c10b28"
SOURCE_DIR = ROOT / "build/source-audit/openetymology" / SOURCE_COMMIT
SOURCE_FILES = {
    "CET4/CET4.txt": {
        "target": "cet4", "mask": 1 << 0, "count": 4533,
        "sha256": "55c074bcb06aaa2fe5aa99b550d255b55d373ef313bc051fa53f9d82231784e0",
    },
    "CET6/CET6.txt": {
        "target": "cet6", "mask": 1 << 1, "count": 2219,
        "sha256": "9a8fa3f2464a39526472211228ef1f331ab1e3d67567b11eea49efc7444d5647",
    },
}
OPEN_TAGS = DATA / "openetymology-exam-tags.tsv"
OPEN_TAG_MANIFEST = DATA / "openetymology-tags-manifest.json"
CET_TAGS = DATA / "openetymology-cet-tags.tsv"
CET_TAG_MANIFEST = DATA / "openetymology-cet-tags-manifest.json"
ECDICT = ROOT / "build/vocabulary-research/skywind3000__ECDICT/ecdict.csv"
BASELINE = ROOT / "build/expansion-base.tsv"
PINYIN = ROOT / "build/pinyin-candidates.tsv"
UK_IPA = ROOT / "pronunciation/source/en_UK.txt"
US_IPA = ROOT / "pronunciation/source/en_US.txt"
PINYIN_OVERLAYS = (
    (DATA / "pinyin-overlays/exam-target-batch-11.tsv",
     "a42e86df9afbf2a6a811cb2e844545c8e1b4b6df40fcf81f1dd333ef0be7d859"),
    (DATA / "pinyin-overlays/exam-target-batch-12.tsv",
     "60c6e0648bfe16e18566088db22ef51fde8437c42ce314843774f6691e13b1d9"),
    (DATA / "pinyin-overlays/exam-target-batch-13.tsv",
     "2bff3ae926be131d4edc0f1871dfecc566889d24e0d4d62838972372a3a94fb5"),
)
CURATION = DATA / "batches/29-openetymology-cet-review.tsv"
CANDIDATES = DATA / "batches/29-openetymology-cet-candidates.tsv"
REVIEWED = DATA / "batches/29-openetymology-cet-reviewed.tsv"
EXPANSION = DATA / "openetymology-cet-expansion.tsv"
MANIFEST = DATA / "openetymology-cet-manifest.json"
ECDICT_SHA256 = "1a6947e04785db63613a92e14903cdae7954f7e84860b10e68e5c7cbb3f9c3cf"
EXPECTED = {
    "baseline": "ed58a90825243beada4d759f2f90d55ccdb4d38fc8701dffd78090e3a0b21d35",
    "pinyin": "914f6894fff1f6033af6d8bb9858f6901aa2d1a960cd2afd8923f899584f1290",
    "uk_ipa": "221394caef0cf723b4f2df81a98ac33191293257b88aed5b1fb89466d3a0dc77",
    "us_ipa": "2af6f154a5c363275f052d1f85acedef38ed185ca9745aa4314be77f6b70de67",
}
MAX_EXTRA_PER_KEY = 8
TARGET_BITS = {"cet4": 1 << 0, "cet6": 1 << 1, "tem4": 1 << 2,
               "tem8": 1 << 3, "toefl": 1 << 4, "ielts": 1 << 5}


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def tsv_bytes(fields: tuple[str, ...], rows: list[dict[str, str]], *, header: bool = True) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t", lineterminator="\n")
    if header:
        writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def checked(path: Path, expected: str | None = None) -> bytes:
    if not path.is_file():
        raise SystemExit(f"Missing pinned input: {path}")
    payload = path.read_bytes()
    actual = sha(payload)
    if expected is not None and actual != expected:
        raise SystemExit(f"Pinned input SHA-256 mismatch for {path}: {actual}")
    return payload


def load_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def build() -> tuple[dict[Path, bytes], dict[str, object]]:
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_wiktionary_expansion import read_expansion
    from exam_targets import RUNTIME_EXPANSIONS
    from prepare_candidate_batch import parse_pinyin_candidates, source_pos_glosses
    from prepare_cet_batch import load_base

    open_manifest = json.loads(OPEN_TAG_MANIFEST.read_text(encoding="utf-8"))
    cet_manifest = json.loads(CET_TAG_MANIFEST.read_text(encoding="utf-8"))
    if open_manifest["commit"] != SOURCE_COMMIT or open_manifest["license"] != "CC BY-SA 4.0":
        raise SystemExit("Unexpected OpenEtymology tag source or license")
    if cet_manifest["commit"] != SOURCE_COMMIT or cet_manifest["license"] != "CC BY-SA 4.0":
        raise SystemExit("Unexpected OpenEtymology CET tag source or license")
    open_payload = checked(OPEN_TAGS, open_manifest["output"]["sha256"])
    cet_payload = checked(CET_TAGS, cet_manifest["output"]["sha256"])
    all_tags = {word: int(mask) for word, mask in
                (line.split("\t") for line in open_payload.decode("utf-8").splitlines())}
    cet_tags = {word: int(mask) for word, mask in
                (line.split("\t") for line in cet_payload.decode("utf-8").splitlines())}
    for word, mask in cet_tags.items():
        all_tags[word] = all_tags.get(word, 0) | mask

    source_lists: dict[str, set[str]] = {}
    source_hashes: dict[str, str] = {}
    for relative, record in SOURCE_FILES.items():
        payload = checked(SOURCE_DIR / relative, record["sha256"])
        words = [line.strip().casefold() for line in payload.decode("utf-8-sig").splitlines() if line.strip()]
        if len(words) != record["count"] or len(words) != len(set(words)):
            raise SystemExit(f"Unexpected OpenEtymology source list: {relative}")
        if any(word not in cet_tags or not cet_tags[word] & record["mask"] for word in words):
            raise SystemExit(f"OpenEtymology runtime membership is incomplete: {relative}")
        source_lists[record["target"]] = set(words)
        source_hashes[relative] = sha(payload)

    input_hashes = {
        "openetymology_exam_tags": sha(open_payload),
        "openetymology_cet_tags": sha(cet_payload),
        "ecdict": sha(checked(ECDICT, ECDICT_SHA256)),
        "baseline": sha(checked(BASELINE, EXPECTED["baseline"])),
        "pinyin": sha(checked(PINYIN, EXPECTED["pinyin"])),
        "uk_ipa": sha(checked(UK_IPA, EXPECTED["uk_ipa"])),
        "us_ipa": sha(checked(US_IPA, EXPECTED["us_ipa"])),
    }
    for overlay_path, expected_hash in PINYIN_OVERLAYS:
        input_hashes[overlay_path.name] = sha(checked(overlay_path, expected_hash))

    base = load_base(BASELINE)
    pinyin = parse_pinyin_candidates(PINYIN)
    for overlay_path, _ in PINYIN_OVERLAYS:
        for line_number, line in enumerate(overlay_path.read_text(encoding="utf-8").splitlines(), 1):
            fields = line.split("\t")
            if len(fields) != 4:
                raise SystemExit(f"Invalid pinyin overlay row {overlay_path.name}:{line_number}")
            chinese, reading, frequency, source = fields
            if not reading or not source or int(frequency) != 0:
                raise SystemExit(f"Unexpected pinyin overlay metadata {overlay_path.name}:{line_number}")
            pinyin.setdefault(chinese, (reading, int(frequency)))
    ipa: dict[str, dict[str, str]] = {"uk": {}, "us": {}}
    for locale, path in (("uk", UK_IPA), ("us", US_IPA)):
        for line in path.read_text(encoding="utf-8").splitlines():
            if "\t" in line:
                word, sound = line.split("\t", 1)
                ipa[locale][word.strip().casefold()] = sound.strip()

    existing_pairs = {(word.casefold(), chinese, pos)
                      for chinese, senses in base.items() for word, pos in senses}
    existing_words = {word for word, _, _ in existing_pairs}
    extra_counts: collections.Counter[str] = collections.Counter()
    runtime_files = [name for name in RUNTIME_EXPANSIONS if name != EXPANSION.name]
    for filename in runtime_files:
        path = DATA / filename
        for row in read_expansion(path):
            word, chinese, pos = row["english"].casefold(), row["chinese"], row["pos"]
            existing_pairs.add((word, chinese, pos))
            existing_words.add(word)
            extra_counts[chinese] += 1

    targets_by_word: dict[str, list[str]] = {}
    for word, mask in all_tags.items():
        targets_by_word[word] = [name for name, bit in TARGET_BITS.items() if mask & bit]

    missing_heads = set().union(*source_lists.values()) - existing_words
    candidate_rows: dict[tuple[str, str, str], dict[str, str]] = {}
    ecdict_heads: set[str] = set()
    pinyin_heads: set[str] = set()
    ipa_heads: set[str] = set()
    with ECDICT.open(encoding="utf-8-sig", newline="") as stream:
        for line_number, entry in enumerate(csv.DictReader(stream), start=2):
            word = entry["word"].strip().casefold()
            if word not in missing_heads:
                continue
            glosses = list(source_pos_glosses(entry.get("translation", "")))
            if glosses:
                ecdict_heads.add(word)
            if word in ipa["uk"] or word in ipa["us"]:
                ipa_heads.add(word)
            for chinese, pos in glosses:
                if chinese not in pinyin:
                    continue
                pinyin_heads.add(word)
                if word not in ipa["uk"] and word not in ipa["us"]:
                    continue
                if extra_counts[chinese] >= MAX_EXTRA_PER_KEY:
                    continue
                key = (word, chinese, pos)
                row = candidate_rows.setdefault(key, {
                    "word": word,
                    "chinese": chinese,
                    "pos": pos,
                    "targets": ",".join(targets_by_word[word]),
                    "pinyin": pinyin[chinese][0],
                    "pinyin_frequency": str(pinyin[chinese][1]),
                    "ecdict_rows": str(line_number),
                    "ecdict_translation": entry.get("translation", "").replace("\n", r"\n"),
                    "uk_ipa": ipa["uk"].get(word, ""),
                    "us_ipa": ipa["us"].get(word, ""),
                    "existing_chinese_senses": " | ".join(
                        f"{sense} [{sense_pos}]" for sense, sense_pos in base.get(chinese, [])),
                    "existing_extra_count": str(extra_counts[chinese]),
                })
                if line_number not in {int(value) for value in row["ecdict_rows"].split(",")}:
                    row["ecdict_rows"] += f",{line_number}"

    candidates = [candidate_rows[key] for key in sorted(candidate_rows)]
    curation_rows = load_tsv(CURATION)
    decisions = {(row["word"], row["chinese"], row["pos"]): row for row in curation_rows}
    candidate_keys = {(row["word"], row["chinese"], row["pos"]) for row in candidates}
    if set(decisions) != candidate_keys:
        missing = sorted(candidate_keys - set(decisions))
        stale = sorted(set(decisions) - candidate_keys)
        raise SystemExit(f"Review decisions stale/incomplete; missing={missing!r}; stale={stale!r}")
    if any(row["decision"] not in {"accept", "reject", "defer"} or not row["review_note"].strip()
           for row in curation_rows):
        raise SystemExit("Every candidate needs a decision and review note")

    accepted: list[dict[str, str]] = []
    reviewed: list[dict[str, str]] = []
    accepted_words: set[str] = set()
    mapped_before_words = set(existing_words)
    for candidate in candidates:
        key = (candidate["word"], candidate["chinese"], candidate["pos"])
        decision = decisions[key]
        reviewed.append({**candidate, **decision})
        if decision["decision"] != "accept":
            continue
        if candidate["word"] in mapped_before_words:
            raise SystemExit(f"Accepted word became mapped upstream: {candidate['word']}")
        if extra_counts[candidate["chinese"]] >= MAX_EXTRA_PER_KEY:
            raise SystemExit(f"Accepted row exceeds runtime per-key cap: {candidate['chinese']}")
        accepted.append(candidate)
        accepted_words.add(candidate["word"])
        extra_counts[candidate["chinese"]] += 1

    candidate_fields = (
        "word", "chinese", "pos", "targets", "pinyin", "pinyin_frequency", "ecdict_rows",
        "ecdict_translation", "uk_ipa", "us_ipa", "existing_chinese_senses", "existing_extra_count",
    )
    review_fields = candidate_fields + ("decision", "review_note")
    candidate_payload = tsv_bytes(candidate_fields, candidates)
    reviewed_payload = tsv_bytes(review_fields, reviewed)
    expansion_rows = [
        {"chinese": row["chinese"], "english": row["word"], "pos": row["pos"], "source": "ECDICT MIT"}
        for row in accepted
    ]
    expansion_payload = tsv_bytes(("chinese", "english", "pos", "source"), expansion_rows, header=False)

    mapped_before = {word for word, _, _ in existing_pairs}
    mapped_after = mapped_before | accepted_words
    current_reachable = {word for word, chinese, _ in existing_pairs if chinese in pinyin}
    reachable_after = current_reachable | {row["word"] for row in accepted}
    coverage = {}
    for target, words in source_lists.items():
        before = len(words & mapped_before)
        after = len(words & mapped_after)
        reachable_before = len(words & current_reachable)
        reachable_new = len(words & reachable_after)
        coverage[target] = {
            "source_words": len(words),
            "mapped_before": before,
            "mapped_after": after,
            "mapped_percent_after": round(100 * after / len(words), 2),
            "pinyin_reachable_before": reachable_before,
            "pinyin_reachable_after": reachable_new,
            "pinyin_reachable_percent_after": round(100 * reachable_new / len(words), 2),
            "new_tag_memberships_missing_from_ECDICT_KyleBing": sum(
                not (int(mask1) | int(mask2)) & TARGET_BITS[target]
                for word, mask1, mask2 in (
                    line.split("\t") for line in (DATA / "english-tags.tsv").read_text(encoding="utf-8").splitlines())
                if word in words),
        }

    manifest = {
        "batch": "29-openetymology-cet4-cet6",
        "source": "openetymology/OpenEtymology",
        "source_commit": SOURCE_COMMIT,
        "license": "CC BY-SA 4.0 for list-derived selection and membership; ECDICT MIT for gloss mappings",
        "source_files": {
            relative: {"target": record["target"], "words": record["count"],
                       "sha256": source_hashes[relative],
                       "url": f"https://github.com/openetymology/OpenEtymology/blob/{SOURCE_COMMIT}/{relative}"}
            for relative, record in SOURCE_FILES.items()
        },
        "input_sha256": input_hashes,
        "candidate_gate": {
            "unmapped_source_headwords": len(missing_heads),
            "with_ECDICT_gloss": len(ecdict_heads),
            "with_local_IPA": len(ipa_heads),
            "with_inputtable_pinyin_gloss": len(pinyin_heads),
            "fully_eligible_pairs": len(candidates),
            "manual_review": "Every eligible pair has an explicit accept/reject/defer decision.",
        },
        "review": {
            "accepted_pairs": len(accepted),
            "new_english_headwords": len({row["word"] for row in accepted}),
            "rejected_pairs": sum(row["decision"] == "reject" for row in reviewed),
            "deferred_pairs": sum(row["decision"] == "defer" for row in reviewed),
            "candidates_sha256": sha(candidate_payload),
            "reviewed_sha256": sha(reviewed_payload),
            "curation_sha256": sha(CURATION.read_bytes()),
        },
        "coverage": coverage,
        "runtime_file": {"path": EXPANSION.name, "rows": len(expansion_rows),
                         "bytes": len(expansion_payload), "sha256": sha(expansion_payload)},
        "runtime_notes": "The input path is indexed once with the other compact TSV expansions; no source text is scanned during keystrokes. Chinese candidate ordering is unchanged.",
        "scope_note": "These are community reference wordbooks, not official complete syllabi. Coverage is against these two pinned lists only.",
    }
    manifest_payload = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return {
        CANDIDATES: candidate_payload,
        REVIEWED: reviewed_payload,
        EXPANSION: expansion_payload,
        MANIFEST: manifest_payload,
    }, manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    outputs, manifest = build()
    if args.check:
        changed = [str(path) for path, payload in outputs.items()
                   if not path.is_file() or path.read_bytes() != payload]
        if changed:
            raise SystemExit("OpenEtymology CET batch differs: " + ", ".join(changed))
    elif args.apply:
        for path, payload in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
