"""Build a small, separately licensed CC-CEDICT CET vocabulary tranche."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

from prepare_cet_batch import coverage, load_base


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
BATCHES = DATA / "batches"
INPUT = BATCHES / "04-cc-cedict-review-input.tsv"
REVIEWED = BATCHES / "04-cc-cedict-reviewed.tsv"
OUTPUT = DATA / "cccedict-expansion.tsv"
MANIFEST = DATA / "cccedict-manifest.json"
BASELINE = ROOT / "build/expansion-base.tsv"
PINYIN = ROOT / "build/pinyin-candidates.tsv"
AUDIT = ROOT / "build/source-audit/cc-cedict/cet-pinyin-candidates.tsv"
SOURCE = ROOT / "build/source-audit/cc-cedict/cedict_ts_june2026.u8"
SOURCE_REPO = "TeaPearce/chinese-english-dictionary"
SOURCE_COMMIT = "a9aea223269eb9820590e5bca783eb299c317439"
SOURCE_PATH = "data/cedict_ts_june2026.u8"
SOURCE_SHA256 = "8172061b2a647dd8a179788830ef233944baee479bc7018f111064ad16d8f46f"
SOURCE_URL = f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/{SOURCE_PATH}"
SOURCE_LABEL = "CC-CEDICT CC BY-SA 4.0"
TARGETS = ("cet4", "cet6", "tem4", "tem8", "toefl", "ielts")
ALLOWED_POS = {"n.", "v.", "adj.", "adv.", "pron.", "prep.", "conj.", "num.", "m.", "part.", "int.", "phr."}
LIMIT = 8
MIN_PINYIN_FREQUENCY = 1000
HAN = re.compile(r"[\u4e00-\u9fff]{2,6}")
CEDICT_ENTRY = re.compile(r"^(\S+)\s+(\S+)\s+\[([^]]+)\]\s+/(.*)/\s*$")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def read_expansion(path: Path) -> list[dict[str, str]]:
    names = ("chinese", "english", "pos", "source")
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.split("\t")
        if len(fields) != len(names):
            raise ValueError(f"Invalid expansion row in {path}: {line!r}")
        rows.append(dict(zip(names, fields)))
    return rows


def exam_inputs():
    tags = {}
    for line in (DATA / "english-tags.tsv").read_text(encoding="utf-8").splitlines():
        word, first, second = line.split("\t")
        tags[word] = int(first) | int(second)
    pinyin = {}
    for line in PINYIN.read_text(encoding="utf-8").splitlines():
        chinese, code, frequency = line.split("\t")
        pinyin[chinese] = (code, int(frequency))
    ipa = set()
    for filename in ("en_UK.txt", "en_US.txt"):
        for line in (ROOT / "pronunciation/source" / filename).read_text(encoding="utf-8").splitlines():
            if "\t" in line:
                ipa.add(line.split("\t", 1)[0].strip().lower())
    return tags, pinyin, ipa


def exact_pos_evidence(candidate: dict[str, str], pos: str) -> list[str]:
    return sorted({part.strip() for part in candidate["pos"].split(" | ")
                   if part.strip().startswith(pos + " ")})


def build_payloads(
    input_path: Path = INPUT,
    reviewed_path: Path = REVIEWED,
    output_path: Path = OUTPUT,
    manifest_path: Path = MANIFEST,
    batch_name: str = "02-cc-cedict-1",
    minimum_frequency: int = MIN_PINYIN_FREQUENCY,
    prior_runtime_paths: tuple[Path, ...] = (),
):
    if not SOURCE.is_file() or sha(SOURCE) != SOURCE_SHA256:
        raise ValueError("Missing or changed pinned CC-CEDICT snapshot: " + str(SOURCE))
    data_manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    ecdict_source = next(row for row in data_manifest["input_files"] if row["path"] == "ecdict.csv")
    audit_manifest = json.loads((AUDIT.parent / "summary.json").read_text(encoding="utf-8"))
    if audit_manifest["source"]["sha256"] != SOURCE_SHA256:
        raise ValueError("CC-CEDICT audit summary points to a different snapshot")
    if audit_manifest["pinned_tag_sha256"] != sha(DATA / "english-tags.tsv"):
        raise ValueError("The CC-CEDICT audit must be regenerated after exam-tag changes")
    if audit_manifest["pinyin_candidates_sha256"] != sha(PINYIN):
        raise ValueError("The CC-CEDICT audit must be regenerated after pinyin-index changes")
    if audit_manifest["pinned_ecdict_sha256"] != ecdict_source["sha256"]:
        raise ValueError("The CC-CEDICT audit was not validated against the pinned ECDICT")
    if audit_manifest.get("candidate_tsv_sha256") != sha(AUDIT):
        raise ValueError("CC-CEDICT audit TSV checksum mismatch")
    source_lines = SOURCE.read_text(encoding="utf-8").splitlines()
    audit_rows = read_tsv(AUDIT)
    audit_by_pair: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in audit_rows:
        audit_by_pair.setdefault((row["word"], row["chinese"]), []).append(row)

    tags, pinyin, ipa = exam_inputs()
    base = load_base(BASELINE)
    original = read_expansion(DATA / "english-expansion.tsv")
    wiktionary = read_expansion(DATA / "wiktionary-expansion.tsv")
    existing_words = {word for senses in base.values() for word, _ in senses}
    existing_words.update(row["english"] for row in original + wiktionary)
    existing_pairs = {(row["chinese"], row["english"]) for row in original + wiktionary}
    extra_count: dict[str, int] = {}
    for row in original + wiktionary:
        extra_count[row["chinese"]] = extra_count.get(row["chinese"], 0) + 1
    prior_rows = []
    for path in prior_runtime_paths:
        rows = read_expansion(path)
        prior_rows.extend(rows)
        existing_words.update(row["english"] for row in rows)
        existing_pairs.update((row["chinese"], row["english"]) for row in rows)
        for row in rows:
            extra_count[row["chinese"]] = extra_count.get(row["chinese"], 0) + 1

    curation = read_tsv(input_path)
    required_input = {"word", "chinese", "pos", "review_note"}
    if not curation or set(curation[0]) != required_input:
        raise ValueError("Unexpected CC-CEDICT review input schema")
    input_words: set[str] = set()
    selected = []
    deferred = []
    for item in curation:
        word, chinese, pos = item["word"].strip().lower(), item["chinese"], item["pos"]
        if word in input_words:
            raise ValueError("Duplicate reviewed headword: " + word)
        input_words.add(word)
        if not re.fullmatch(r"[a-z]+(?:[-'][a-z]+)*", word):
            raise ValueError("Invalid English headword: " + word)
        if not HAN.fullmatch(chinese) or chinese not in base or chinese not in pinyin:
            raise ValueError("Chinese gloss is not an exact packed pinyin key: " + chinese)
        if pos not in ALLOWED_POS:
            raise ValueError("Unsupported part of speech: " + pos)
        if word not in tags or not tags[word] & 3:
            raise ValueError("Headword is not CET4/CET6 tagged: " + word)
        if word in existing_words or (chinese, word) in existing_pairs:
            raise ValueError("Headword is already mapped in shipped data: " + word)
        if word not in ipa:
            raise ValueError("No bundled IPA for headword: " + word)
        if not item["review_note"].strip():
            raise ValueError("Missing manual sense review: " + word)

        candidates = [row for row in audit_by_pair.get((word, chinese), [])
                      if row["match_kind"] in {"exact", "to-verb"}
                      and exact_pos_evidence(row, pos)]
        if not candidates:
            raise ValueError(f"No exact CEDICT gloss and ECDICT POS evidence: {word} -> {chinese}")
        candidate = max(candidates, key=lambda row: (int(row["pinyin_frequency"]), -int(row["source_line"])))
        mask = tags[word]
        actual_targets = [target for bit, target in enumerate(TARGETS) if mask & (1 << bit)]
        actual_cet_targets = [target for bit, target in enumerate(TARGETS[:2]) if mask & (1 << bit)]
        if candidate["targets"].split(",") != actual_cet_targets:
            raise ValueError("Audit target tag disagrees with local tag index: " + word)
        if int(candidate["pinyin_frequency"]) != pinyin[chinese][1]:
            raise ValueError("Pinyin candidate frequency mismatch: " + chinese)

        line_number = int(candidate["source_line"])
        if line_number < 1 or line_number > len(source_lines):
            raise ValueError("CC-CEDICT source line is outside the pinned snapshot")
        match = CEDICT_ENTRY.fullmatch(source_lines[line_number - 1])
        if not match:
            raise ValueError(f"Pinned CC-CEDICT line {line_number} no longer parses")
        traditional, simplified, cedict_pinyin, raw_definitions = match.groups()
        gloss = candidate["english_gloss"]
        if simplified != chinese or gloss not in {word, "to " + word}:
            raise ValueError(f"CC-CEDICT line {line_number} does not support {word} -> {chinese}")
        if gloss not in [definition.strip().lower() for definition in raw_definitions.split("/")]:
            raise ValueError(f"CC-CEDICT gloss is not an exact whole definition: {word} -> {chinese}")

        entry = {
            "word": word,
            "chinese": chinese,
            "pos": pos,
            "target_tags": ",".join(actual_targets),
            "ecdict_pos_evidence": "; ".join(exact_pos_evidence(candidate, pos)),
            "cedict_english_gloss": gloss,
            "match_kind": candidate["match_kind"],
            "cedict_pinyin": cedict_pinyin,
            "traditional": traditional,
            "pinyin": candidate["pinyin"],
            "pinyin_frequency": candidate["pinyin_frequency"],
            "source_line": str(line_number),
            "source_url": f"https://github.com/{SOURCE_REPO}/blob/{SOURCE_COMMIT}/{SOURCE_PATH}",
            "review_note": item["review_note"],
        }
        if int(candidate["pinyin_frequency"]) >= minimum_frequency:
            selected.append(entry)
        else:
            deferred.append(entry)

    capacities = dict(extra_count)
    for row in selected:
        key = row["chinese"]
        if capacities.get(key, 0) >= LIMIT:
            raise ValueError("The Chinese key would exceed the eight-extra limit: " + key)
        capacities[key] = capacities.get(key, 0) + 1

    reviewed_columns = tuple(selected[0])
    reviewed_payload = ("\t".join(reviewed_columns) + "\n" + "".join(
        "\t".join(row[name].replace("\t", " ").replace("\n", " ") for name in reviewed_columns) + "\n"
        for row in selected
    )).encode("utf-8")
    runtime_payload = "".join(
        f"{row['chinese']}\t{row['word']}\t{row['pos']}\t{SOURCE_LABEL}\n" for row in selected
    ).encode("utf-8")

    all_words = existing_words | {row["word"] for row in selected}
    pinyin_keys = set(pinyin)
    reachable_before = {
        word for chinese, senses in base.items() if chinese in pinyin_keys for word, _ in senses
    } | {row["english"] for row in original + wiktionary if row["chinese"] in pinyin_keys}
    reachable_after = reachable_before | {row["word"] for row in selected}
    before_coverage = coverage(tags, existing_words, ipa)
    after_coverage = coverage(tags, all_words, ipa)
    input_sha = sha(input_path)
    if batch_name == "02-cc-cedict-1" and minimum_frequency == MIN_PINYIN_FREQUENCY:
        selection_rule = (
            f"First tranche requires exact pinyin-key frequency >= {MIN_PINYIN_FREQUENCY}; "
            "lower-frequency manually reviewed candidates are deferred without being rejected."
        )
    elif minimum_frequency == 0:
        selection_rule = "All individually reviewed candidates with an exact packed pinyin key are included, regardless of frequency."
    else:
        selection_rule = (
            f"This reviewed tranche requires exact pinyin-key frequency >= {minimum_frequency}; "
            "lower-frequency manually reviewed candidates are deferred without being rejected."
        )
    manifest = {
        "batch": batch_name,
        "selection_rule": selection_rule,
        "source": {
            "project": "CC-CEDICT",
            "attribution": "MDBG and CC-CEDICT contributors",
            "license": "CC BY-SA 4.0",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "official_download_and_license": "https://cc-cedict.org/editor/editor.php?handler=Download",
            "snapshot": "June 2026 CC-CEDICT text mirrored in a pinned GitHub commit",
            "mirror_repo": f"https://github.com/{SOURCE_REPO}",
            "commit": SOURCE_COMMIT,
            "path": SOURCE_PATH,
            "url": SOURCE_URL,
            "sha256": sha(SOURCE),
            "bytes": SOURCE.stat().st_size,
        },
        "audited_source": {
            "summary_sha256": sha(AUDIT.parent / "summary.json"),
            "candidate_file_sha256": sha(AUDIT),
            "candidate_rows": len(audit_rows),
            "source_line_numbers_resolved_against_snapshot": True,
        },
        "validation_inputs": {
            "manual_review_input": {"path": input_path.relative_to(DATA).as_posix(), "sha256": input_sha, "rows": len(curation)},
            "english_exam_tags_sha256": sha(DATA / "english-tags.tsv"),
            "pinyin_candidates_sha256": sha(PINYIN),
            "pinned_ecdict_sha256": ecdict_source["sha256"],
        },
        "curation_file": {"path": reviewed_path.relative_to(DATA).as_posix(), "sha256": hashlib.sha256(reviewed_payload).hexdigest(), "rows": len(selected)},
        "runtime_file": {"path": output_path.relative_to(DATA).as_posix(), "sha256": hashlib.sha256(runtime_payload).hexdigest(), "bytes": len(runtime_payload), "rows": len(selected)},
        "added_pairs": len(selected),
        "added_headwords": len({row["word"] for row in selected}),
        "added_candidate_keys": len({row["chinese"] for row in selected}),
        "added_headwords_by_target": {
            target: sum(bool(tags[row["word"]] & (1 << bit)) for row in selected)
            for bit, target in enumerate(TARGETS)
        },
        "manual_reviewed_but_deferred_rows": len(deferred),
        "manual_reviewed_but_deferred_headwords": len({row["word"] for row in deferred}),
        "deferred_frequency_range": [min((int(row["pinyin_frequency"]) for row in deferred), default=0),
                                     max((int(row["pinyin_frequency"]) for row in deferred), default=0)],
        "pending_cet_headwords_before": sum(bool(mask & 3) and word not in existing_words for word, mask in tags.items()),
        "pending_cet_headwords_after": sum(bool(mask & 3) and word not in all_words for word, mask in tags.items()),
        "coverage_before": before_coverage,
        "coverage_after": after_coverage,
        "candidate_reachable_coverage_before": coverage(tags, reachable_before, ipa),
        "candidate_reachable_coverage_after": coverage(tags, reachable_after, ipa),
        "review_rule": "Every runtime row is an exact whole CC-CEDICT English gloss on a pinned source line, with simplified Chinese matching the packed pinyin key and an existing English IPA. POS is checked against pinned ECDICT; sense notes are manually curated. Original translations and Chinese candidate ordering are unchanged.",
        "license_boundary": "The CC-CEDICT-derived runtime rows and source-attributed curation records are CC BY-SA 4.0 and remain separate from MIT/BSD expansions. POS audit labels are cross-checked against ECDICT (MIT); runtime rows do not include ECDICT definitions. No complete CC-CEDICT file is distributed.",
        "limitations": "CC-CEDICT supplies Chinese-to-English glosses without POS. Exact gloss matching and manual review reduce ambiguity but do not imply an authoritative exam list or complete word-sense coverage. Pinyin frequency ranks candidate surfaces; a reachable key may still be below the first candidate page.",
    }
    if prior_runtime_paths:
        manifest["prior_cc_cedict_runtime_files"] = [
            {"path": path.relative_to(DATA).as_posix(), "sha256": sha(path), "rows": len(read_expansion(path))}
            for path in prior_runtime_paths
        ]
    return {
        reviewed_path: reviewed_payload,
        output_path: runtime_payload,
        manifest_path: (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
    }, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write generated review data, runtime rows, and manifest")
    parser.add_argument("--input", type=Path, default=INPUT, help="manually reviewed candidate TSV")
    parser.add_argument("--reviewed-output", type=Path, default=REVIEWED)
    parser.add_argument("--runtime-output", type=Path, default=OUTPUT)
    parser.add_argument("--manifest-output", type=Path, default=MANIFEST)
    parser.add_argument("--batch-name", default="02-cc-cedict-1")
    parser.add_argument("--minimum-frequency", type=int, default=MIN_PINYIN_FREQUENCY)
    parser.add_argument("--prior-runtime", type=Path, action="append", default=[])
    args = parser.parse_args()
    if args.minimum_frequency < 0:
        parser.error("--minimum-frequency cannot be negative")
    outputs, manifest = build_payloads(
        input_path=args.input.resolve(),
        reviewed_path=args.reviewed_output.resolve(),
        output_path=args.runtime_output.resolve(),
        manifest_path=args.manifest_output.resolve(),
        batch_name=args.batch_name,
        minimum_frequency=args.minimum_frequency,
        prior_runtime_paths=tuple(path.resolve() for path in args.prior_runtime),
    )
    for path, payload in outputs.items():
        if args.apply:
            path.write_bytes(payload)
        elif not path.is_file() or path.read_bytes() != payload:
            raise SystemExit(f"Generated file differs; run with --apply: {path}")
    print(json.dumps({key: manifest[key] for key in (
        "batch", "added_pairs", "added_headwords", "added_candidate_keys",
        "manual_reviewed_but_deferred_rows", "pending_cet_headwords_before",
        "pending_cet_headwords_after", "coverage_before", "coverage_after",
        "candidate_reachable_coverage_after")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
