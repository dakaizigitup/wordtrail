"""Build a pinned WordLevel TOEFL/IELTS membership and ECDICT mapping batch."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
SOURCE_DIR = DATA / "sources/wordlevel"
SOURCE_CSV = SOURCE_DIR / "toefl_essential_vocabulary.csv"
SOURCE_README = SOURCE_DIR / "README.md"
SOURCE_LICENSE = SOURCE_DIR / "LICENSE"
SOURCE_COMMIT = "85d4392a2254d2a1ad73cf12cdd8898b49cd3295"
SOURCE_CSV_SHA256 = "2c780f2cc35da4efb0ec2bc28b6011de63d4b580fc61e6768aab62a3eba81099"
SOURCE_README_SHA256 = "fc40e931f52d3cea409e736f8000c5153e2fde2fdb691eb49f0345a43453c17a"
SOURCE_LICENSE_SHA256 = "d47290ccbc3c29e257e3ee660897a915dd9f796a78ca1027e9ab09be4903e578"
ECDICT = ROOT / "build/vocabulary-research/skywind3000__ECDICT/ecdict.csv"
ECDICT_SHA256 = "1a6947e04785db63613a92e14903cdae7954f7e84860b10e68e5c7cbb3f9c3cf"
BASELINE = ROOT / "build/expansion-base.tsv"
PINYIN = ROOT / "build/pinyin-candidates.tsv"
UK_IPA = ROOT / "pronunciation/source/en_UK.txt"
US_IPA = ROOT / "pronunciation/source/en_US.txt"
REVIEWED = DATA / "batches/28-wordlevel-reviewed.tsv"
TAG_EVIDENCE = DATA / "batches/28-wordlevel-tag-evidence.tsv"
EXPANSION = DATA / "wordlevel-toefl-ielts-expansion.tsv"
TAGS = DATA / "wordlevel-toefl-ielts-tags.tsv"
MANIFEST = DATA / "wordlevel-toefl-ielts-manifest.json"

SOURCE_LABEL = "WordLevel TOEFL/IELTS Academic List"
EXPANSION_SOURCE = "ECDICT MIT"
TOEFL_IELTS_MASK = (1 << 4) | (1 << 5)
WORD = re.compile(r"[a-z]+(?:[-'][a-z]+)*\Z")
EXTRA_CAP = 8
SOURCE_EXCLUSIONS = {
    "inasmuchas": "Malformed fused phrase: the source example uses 'inasmuch as'; this is not a single-word headword.",
}

# Decisions are tied to the pinned ECDICT glosses, the exact WordLevel headword
# and POS, and the current inputtable Chinese key. The WordLevel list supplies
# target membership; ECDICT supplies the Chinese translation.
ACCEPTED = {
    ("畸变", "aberration", "n."): "Exact ECDICT noun gloss; preserves the general distortion/deviation sense.",
    ("课程", "curricula", "n."): "Exact ECDICT noun gloss and a direct rendering of the plural of curriculum.",
    ("掩盖", "enshroud", "v."): "Exact ECDICT verb gloss; matches the core sense 'cover and hide'.",
    ("隐蔽", "enshroud", "v."): "Exact ECDICT verb gloss; matches the concealment sense.",
}
REJECTED = {
    ("色差", "aberration", "n."): "Too narrow as a translation of the general headword; it names chromatic aberration specifically.",
    ("优势", "ascendancy", "n."): "Too broad for the defined state of dominant power; ECDICT's more exact 支配地位 is not a current input key.",
    ("装配", "configure", "v."): "Means assemble; the WordLevel computer/software sense is better translated as 配置 or 设置.",
    ("目前", "immediacy", "n."): "Temporal 'currently' gloss does not match the noun meaning of direct, immediate involvement.",
    ("爆裂", "implode", "v."): "Loses the defining inward-collapse meaning; a direct inputtable 内爆 gloss is unavailable.",
    ("利润", "markup", "n."): "Financial markup sense conflicts with WordLevel's computer-science markup-language definition.",
}
DEFERRED = {
    ("非常", "eminently", "adv."): "The gloss is accurate, but this pinyin key already has the maximum eight expansion rows; no alternate inputtable gloss passed the same filters.",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tsv_bytes(fields: tuple[str, ...], rows: list[dict[str, str]], *, header: bool = True) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, delimiter="\t", lineterminator="\n")
    if header:
        writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def checked_hash(path: Path, expected: str | None = None) -> str:
    if not path.is_file():
        raise SystemExit(f"Missing pinned input: {path}")
    actual = sha(path.read_bytes())
    if expected is not None and actual != expected:
        raise SystemExit(f"Pinned input SHA-256 mismatch: {path}")
    return actual


def source_words() -> dict[str, dict[str, str]]:
    checked_hash(SOURCE_CSV, SOURCE_CSV_SHA256)
    checked_hash(SOURCE_README, SOURCE_README_SHA256)
    checked_hash(SOURCE_LICENSE, SOURCE_LICENSE_SHA256)
    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        expected = ("word", "pos", "difficulty", "theme", "synonyms", "definition_en", "example_sentence")
        if tuple(reader.fieldnames or ()) != expected:
            raise SystemExit(f"Unexpected WordLevel CSV columns: {reader.fieldnames}")
        rows: dict[str, dict[str, str]] = {}
        for row in reader:
            word = row["word"].strip().casefold()
            if not WORD.fullmatch(word):
                raise SystemExit(f"Invalid WordLevel headword: {word!r}")
            if word in rows:
                raise SystemExit(f"Duplicate WordLevel headword: {word}")
            rows[word] = row
    if len(rows) != 1000:
        raise SystemExit(f"Expected 1,000 unique WordLevel entries, found {len(rows)}")
    return rows


def local_inputs():
    sys.path.insert(0, str(ROOT / "scripts"))
    from prepare_candidate_batch import parse_pinyin_candidates, source_pos_glosses
    from prepare_cet_batch import load_base

    checked_hash(ECDICT, ECDICT_SHA256)
    base = load_base(BASELINE)
    pinyin = parse_pinyin_candidates(PINYIN)
    ipa = {
        line.split("\t", 1)[0].strip().casefold()
        for path in (UK_IPA, US_IPA)
        for line in path.read_text(encoding="utf-8").splitlines()
        if "\t" in line
    }

    # Read every currently compiled expansion table. The batch being built is
    # excluded so --check remains stable after the new file enters mod.rs.
    expansion_mod = (ROOT / "vocabulary/src/expansion/mod.rs").read_text(encoding="utf-8")
    runtime_files = sorted(set(re.findall(r'include_str!\("\.\./\.\./data/([^\"]+\.tsv)"\)', expansion_mod)))
    runtime_files = [name for name in runtime_files if name != EXPANSION.name]
    expansions: list[tuple[str, str, str, str]] = []
    for name in runtime_files:
        path = DATA / name
        if not path.is_file():
            raise SystemExit(f"Missing compiled vocabulary input: {path}")
        for line in path.read_text(encoding="utf-8").splitlines():
            fields = line.split("\t")
            if len(fields) != 4:
                raise SystemExit(f"Invalid expansion row in {path}: {line!r}")
            expansions.append(tuple(fields))

    prior_tags: dict[str, int] = {}
    for line in (DATA / "english-tags.tsv").read_text(encoding="utf-8").splitlines():
        word, ecdict, kylebing = line.split("\t")
        prior_tags[word] = int(ecdict) | int(kylebing)
    open_tags = DATA / "openetymology-exam-tags.tsv"
    if open_tags.is_file():
        for line in open_tags.read_text(encoding="utf-8").splitlines():
            word, mask = line.split("\t")
            prior_tags[word] = prior_tags.get(word, 0) | int(mask)
    open_cet_tags = DATA / "openetymology-cet-tags.tsv"
    if open_cet_tags.is_file():
        for line in open_cet_tags.read_text(encoding="utf-8").splitlines():
            word, mask = line.split("\t")
            prior_tags[word] = prior_tags.get(word, 0) | int(mask)

    input_files = {
        "wordlevel_csv": SOURCE_CSV,
        "wordlevel_readme": SOURCE_README,
        "wordlevel_license": SOURCE_LICENSE,
        "ecdict": ECDICT,
        "expansion_base": BASELINE,
        "pinyin_candidates": PINYIN,
        "uk_ipa": UK_IPA,
        "us_ipa": US_IPA,
        "english_tags": DATA / "english-tags.tsv",
        "openetymology_exam_tags": open_tags,
        "openetymology_cet_tags": open_cet_tags,
        "expansion_index": ROOT / "vocabulary/src/expansion/mod.rs",
    }
    for number, name in enumerate(runtime_files, start=1):
        input_files[f"runtime_expansion_{number:02d}:{name}"] = DATA / name
    input_hashes = {name: checked_hash(path) for name, path in sorted(input_files.items())}
    return base, pinyin, ipa, expansions, runtime_files, prior_tags, source_pos_glosses, input_hashes


def candidate_rows(words, base, pinyin, ipa, existing_words, source_pos_glosses):
    candidates: dict[tuple[str, str, str], dict[str, str]] = {}
    with ECDICT.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            word = row["word"].strip().casefold()
            if word not in words or word in existing_words or word not in ipa:
                continue
            if word in SOURCE_EXCLUSIONS:
                continue
            for chinese, pos in source_pos_glosses(row.get("translation", "")):
                if chinese not in base or chinese not in pinyin:
                    continue
                if pos not in {base_pos for _, base_pos in base[chinese]}:
                    continue
                key = (chinese, word, pos)
                candidates[key] = {
                    "chinese": chinese,
                    "english": word,
                    "pos": pos,
                    "wordlevel_pos": words[word].get("pos", ""),
                    "wordlevel_theme": words[word].get("theme", ""),
                    "wordlevel_difficulty": words[word].get("difficulty", ""),
                    "pinyin": pinyin[chinese][0],
                    "base_senses": " | ".join(f"{sense} [{sense_pos}]" for sense, sense_pos in base[chinese]),
                    "ecdict_translation": row.get("translation", "").replace("\n", r"\n"),
                }
    expected = set(ACCEPTED) | set(REJECTED) | set(DEFERRED)
    found = set(candidates)
    if found != expected:
        missing = sorted(expected - found)
        unexpected = sorted(found - expected)
        raise SystemExit(f"Reviewed candidate set drift; missing={missing!r}; unexpected={unexpected!r}")
    rows = []
    for key in sorted(candidates):
        row = candidates[key]
        if key in ACCEPTED:
            row["decision"] = "accept"
            row["review_note"] = ACCEPTED[key]
        elif key in DEFERRED:
            row["decision"] = "defer"
            row["review_note"] = DEFERRED[key]
        else:
            row["decision"] = "reject"
            row["review_note"] = REJECTED[key]
        rows.append(row)
    return rows


def build():
    words = source_words()
    base, pinyin, ipa, expansions, runtime_files, prior_tags, source_pos_glosses, input_hashes = local_inputs()
    existing_words = {word.casefold() for senses in base.values() for word, _ in senses}
    existing_words.update(english.casefold() for _, english, _, _ in expansions)
    candidates = candidate_rows(words, base, pinyin, ipa, existing_words, source_pos_glosses)

    approved = [row for row in candidates if row["decision"] == "accept"]
    rejected = [row for row in candidates if row["decision"] == "reject"]
    deferred = [row for row in candidates if row["decision"] == "defer"]
    accepted_keys = {(row["chinese"], row["english"], row["pos"]) for row in approved}
    rejected_keys = {(row["chinese"], row["english"], row["pos"]) for row in rejected}
    deferred_keys = {(row["chinese"], row["english"], row["pos"]) for row in deferred}
    if accepted_keys != set(ACCEPTED) or rejected_keys != set(REJECTED) or deferred_keys != set(DEFERRED):
        raise AssertionError("review decisions and candidate rows differ")

    # Keep each accepted translation on its existing pinyin/IPA-capable key and
    # preserve the runtime's per-key expansion cap.
    extra_counts: dict[str, int] = {}
    for chinese, _, _, _ in expansions:
        extra_counts[chinese] = extra_counts.get(chinese, 0) + 1
    for chinese, english, pos in accepted_keys:
        if any(
            base_english.casefold() == english and base_pos == pos
            for base_english, base_pos in base.get(chinese, [])
        ):
            raise SystemExit(f"Accepted pair already exists in base: {chinese} -> {english}")
        if any(row[0] == chinese and row[1].casefold() == english for row in expansions):
            raise SystemExit(f"Accepted pair already exists in runtime: {chinese} -> {english}")
        if extra_counts.get(chinese, 0) >= EXTRA_CAP:
            raise SystemExit(f"Accepted row exceeds runtime per-key cap: {chinese}")
        extra_counts[chinese] = extra_counts.get(chinese, 0) + 1

    reviewed_fields = (
        "chinese", "english", "pos", "wordlevel_pos", "wordlevel_theme", "wordlevel_difficulty",
        "pinyin", "base_senses", "ecdict_translation", "decision", "review_note",
    )
    reviewed_payload = tsv_bytes(reviewed_fields, candidates)
    expansion_rows = [
        {"chinese": row["chinese"], "english": row["english"], "pos": row["pos"], "source": EXPANSION_SOURCE}
        for row in approved
    ]
    expansion_payload = tsv_bytes(("chinese", "english", "pos", "source"), expansion_rows, header=False)

    mapped_before = {word for word in existing_words if word in words}
    mapped_after = mapped_before | {row["english"] for row in approved}
    taggable = sorted(word for word in mapped_after if word in ipa)
    tag_rows = [{"word": word, "mask": str(TOEFL_IELTS_MASK), "source": SOURCE_LABEL} for word in taggable]
    tag_payload = tsv_bytes(("word", "mask", "source"), tag_rows, header=False)

    approved_by_word: dict[str, list[str]] = {}
    for row in approved:
        approved_by_word.setdefault(row["english"], []).append(f"{row['chinese']} [{row['pos']}]")
    evidence_rows = []
    for word, source_row in sorted(words.items()):
        is_mapped_before = word in mapped_before
        has_ipa = word in ipa
        is_mapped_after = word in mapped_after
        prior_mask = prior_tags.get(word, 0)
        included = is_mapped_after and has_ipa and word not in SOURCE_EXCLUSIONS
        reason = SOURCE_EXCLUSIONS.get(word, "") or (
            "indexed: local Chinese translation and IPA" if included else (
                "excluded: no local Chinese translation" if not is_mapped_after else "excluded: no bundled IPA"
            )
        )
        evidence_rows.append({
            "word": word,
            "source_pos": source_row.get("pos", ""),
            "theme": source_row.get("theme", ""),
            "difficulty": source_row.get("difficulty", ""),
            "existing_mapping": str(is_mapped_before).lower(),
            "accepted_new_mappings": " | ".join(sorted(approved_by_word.get(word, []))),
            "has_ipa": str(has_ipa).lower(),
            "prior_exam_mask": str(prior_mask & TOEFL_IELTS_MASK),
            "new_toefl_membership": str(included and not (prior_mask & (1 << 4))).lower(),
            "new_ielts_membership": str(included and not (prior_mask & (1 << 5))).lower(),
            "runtime_indexed": str(included).lower(),
            "reason": reason,
        })
    evidence_payload = tsv_bytes((
        "word", "source_pos", "theme", "difficulty", "existing_mapping", "accepted_new_mappings",
        "has_ipa", "prior_exam_mask", "new_toefl_membership", "new_ielts_membership", "runtime_indexed", "reason",
    ), evidence_rows)

    new_toefl = sum(row["new_toefl_membership"] == "true" for row in evidence_rows)
    new_ielts = sum(row["new_ielts_membership"] == "true" for row in evidence_rows)
    new_any_exam = sum(
        row["new_toefl_membership"] == "true" or row["new_ielts_membership"] == "true"
        for row in evidence_rows
    )
    new_both_exam = sum(
        row["new_toefl_membership"] == "true" and row["new_ielts_membership"] == "true"
        for row in evidence_rows
    )
    source_mapped = sum(row["runtime_indexed"] == "true" for row in evidence_rows)
    manifest = {
        "batch": "28-wordlevel-toefl-ielts-academic-membership",
        "source": {
            "title": "TOEFL Essential Vocabulary Dataset (AI-Enriched)",
            "repository": "https://github.com/gungorkaya-eng/toefl-essential-vocabulary-dataset",
            "commit": SOURCE_COMMIT,
            "backlink": "https://wordlevel.net",
            "author": "Gungor Kaya / WordLevel",
            "github_license_declaration": "MIT; see the included upstream LICENSE and README",
            "mendeley_record": "https://data.mendeley.com/datasets/wfksk94zr9/1",
            "mendeley_license_metadata": "CC BY 4.0",
            "mendeley_license_url": "https://creativecommons.org/licenses/by/4.0/",
            "license_handling": "Retain MIT notice and satisfy CC BY attribution; source declarations differ between the repository and DOI record.",
            "source_list_claim": "GitHub README describes the list as TOEFL iBT and IELTS academic vocabulary; this is community-curated membership, not an official exam syllabus.",
            "source_quality_exclusions": SOURCE_EXCLUSIONS,
            "source_sha256": {
                "toefl_essential_vocabulary.csv": SOURCE_CSV_SHA256,
                "README.md": SOURCE_README_SHA256,
                "LICENSE": SOURCE_LICENSE_SHA256,
            },
        },
        "filters": {
            "runtime_tag_scope": "Source words with at least one local Chinese translation and bundled IPA; assign both source TOEFL and IELTS bits while preserving all existing membership bits.",
            "mapping_scope": "Exact ECDICT short Chinese gloss; matching POS in an existing packed glossary key; exact pinyin candidate; bundled UK or US IPA; individually reviewed.",
            "source_definitions_examples_synonyms_in_runtime": False,
            "runtime_per_key_cap": EXTRA_CAP,
            "chinese_candidate_order_changed": False,
        },
        "counts": {
            "source_records": len(words),
            "existing_mapped_headwords": len(mapped_before),
            "existing_mapped_headwords_with_ipa": sum(word in ipa for word in mapped_before),
            "candidates_reviewed": len(candidates),
            "accepted_mappings": len(approved),
            "rejected_candidates": len(rejected),
            "deferred_candidates": len(deferred),
            "new_english_headwords": len({row["english"] for row in approved}),
            "runtime_tagged_source_headwords": source_mapped,
            "new_toefl_memberships": new_toefl,
            "new_ielts_memberships": new_ielts,
            "headwords_receiving_any_new_exam_membership": new_any_exam,
            "headwords_receiving_both_new_exam_memberships": new_both_exam,
            "source_words_not_runtime_tagged": len(words) - source_mapped,
            "mapping_coverage_before_percent": round(100 * len(mapped_before) / len(words), 2),
            "mapping_coverage_after_percent": round(100 * len(mapped_after) / len(words), 2),
        },
        "input_hashes": input_hashes,
        "output_hashes": {
            "batches/28-wordlevel-reviewed.tsv": sha(reviewed_payload),
            "batches/28-wordlevel-tag-evidence.tsv": sha(evidence_payload),
            "wordlevel-toefl-ielts-expansion.tsv": sha(expansion_payload),
            "wordlevel-toefl-ielts-tags.tsv": sha(tag_payload),
        },
    }
    manifest_payload = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return {
        REVIEWED: reviewed_payload,
        TAG_EVIDENCE: evidence_payload,
        EXPANSION: expansion_payload,
        TAGS: tag_payload,
        MANIFEST: manifest_payload,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--apply", action="store_true", help="write deterministic reviewed/runtime outputs")
    mode.add_argument("--check", action="store_true", help="verify outputs against pinned inputs and decisions")
    args = parser.parse_args()
    outputs = build()
    if args.apply:
        for path, payload in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
    else:
        for path, payload in outputs.items():
            if not path.is_file() or path.read_bytes() != payload:
                raise SystemExit(f"Generated output differs or is missing: {path.relative_to(ROOT)}; run with --apply")
    summary = json.loads(outputs[MANIFEST].decode("utf-8"))
    print(json.dumps(summary["counts"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
