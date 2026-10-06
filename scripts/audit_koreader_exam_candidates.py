"""Build a review-only queue from the pinned KOReader en-zh dictionary.

The upstream StarDict compilation is an audit source only. This script never
changes runtime vocabulary. It keeps exact existing Qingjian pinyin keys,
bundled IPA, exam-tagged missing English headwords, source POS, and source
definition/gloss evidence in a reproducible review table.
"""
from __future__ import annotations

import collections
import csv
import gzip
import hashlib
import html
import json
import re
import struct
import zipfile
from pathlib import Path

from exam_targets import RUNTIME_EXPANSIONS, load_exam_tags
from prepare_cet_batch import load_base
from prepare_candidate_batch import parse_pinyin_candidates
from wordnet_guard import WordNetGuard

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
ARCHIVE = ROOT / "build/source-audit/koreader-dicts/v1.2.0/en-zh.zip"
ARCHIVE_SHA256 = "910d8fc3bf054f7a36f5db134f0624619711e5b414ebf7de45a3c0e04e98232c"
DICT_PREFIX = "en-zh/"
OUTPUT = ROOT / "build/source-audit/exam-targets/koreader-v1.2.0-candidates.tsv"
SUMMARY = ROOT / "build/source-audit/exam-targets/koreader-v1.2.0-candidates.json"
COW_SOURCE = ROOT / "build/source-audit/omw-cow/406bf83b3c507a3d1f26e88252d5d66893fd36bf/wns/cow/wn-data-cmn.tab"
COW_SOURCE_SHA256 = "379fd2e41d3e1395f9f27cf23a39c6181849ffb4020c14a07ed2a4d4dd651122"
TARGETS = ("tem4", "tem8", "toefl", "ielts")
TARGET_BITS = {target: bit for bit, target in enumerate(("cet4", "cet6", *TARGETS))}
WORD = re.compile(r"[a-z]+(?:[-'][a-z]+)*\Z")
DIV = re.compile(r"<div(?:\s[^>]*)?>(.*?)</div>", re.I | re.S)
POS = re.compile(r"<i(?:\s+[^>]*)?>\s*(n|v|adj|adv)\.\s*</i>", re.I)
BOLD = re.compile(r"<b(?:\s[^>]*)?>(.*?)</b>", re.I | re.S)
TAGS = re.compile(r"<[^>]+>")
SPLIT = re.compile(r"[,，、;；/]")
HAN = re.compile(r"[\u3400-\u9fff]{2,6}\Z")
POS_LABEL = {"n": "n.", "v": "v.", "adj": "adj.", "adv": "adv."}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_only(value: str) -> str:
    return " ".join(html.unescape(TAGS.sub(" ", value)).split())


def read_pinned_archive() -> tuple[bytes, bytes]:
    if not ARCHIVE.is_file() or sha(ARCHIVE) != ARCHIVE_SHA256:
        raise SystemExit("Missing or changed pinned KOReader en-zh v1.2.0 archive")
    with zipfile.ZipFile(ARCHIVE) as archive:
        idx = archive.read(DICT_PREFIX + "en-zh.idx")
        compressed_dictionary = archive.read(DICT_PREFIX + "en-zh.dict.dz")
    return idx, gzip.decompress(compressed_dictionary)


def parse_entry(raw: str) -> list[tuple[str, str, int, str]]:
    """Return (POS, exact Chinese gloss, source order, source context) tuples."""
    output = []
    for block in DIV.findall(raw):
        match = POS.search(block)
        if not match:
            continue
        pos = POS_LABEL[match.group(1).lower()]
        context = text_only(block)
        rank = 0
        for bold in BOLD.findall(block):
            gloss = text_only(bold)
            for option in SPLIT.split(gloss):
                option = option.strip()
                if HAN.fullmatch(option):
                    rank += 1
                    output.append((pos, option, rank, context))
    return output


def load_ipa() -> set[str]:
    return {
        line.split("\t", 1)[0].strip().casefold()
        for name in ("en_UK.txt", "en_US.txt")
        for line in (ROOT / "pronunciation/source" / name).read_text(encoding="utf-8").splitlines()
        if "\t" in line
    }


def load_cow() -> dict[tuple[str, str], set[str]]:
    if not COW_SOURCE.is_file() or sha(COW_SOURCE) != COW_SOURCE_SHA256:
        raise SystemExit("Missing or changed pinned Chinese Open Wordnet evidence")
    synset = re.compile(r"(?P<offset>\d{8})-(?P<pos>[nvar])\Z")
    result: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    with COW_SOURCE.open(encoding="utf-8") as stream:
        for raw in stream:
            if not raw.strip() or raw.startswith("#"):
                continue
            fields = raw.rstrip("\r\n").split("\t")
            if len(fields) != 3 or fields[1] != "cmn:lemma":
                continue
            match = synset.fullmatch(fields[0])
            if match and HAN.fullmatch(fields[2].strip()):
                result[(match["pos"], match["offset"])].add(fields[2].strip())
    return result


def main() -> None:
    idx, dictionary = read_pinned_archive()
    tags = load_exam_tags(DATA)
    base = load_base(ROOT / "build/expansion-base.tsv")
    pinyin = parse_pinyin_candidates(ROOT / "build/pinyin-candidates.tsv")
    ipa = load_ipa()
    cow = load_cow()
    guard = WordNetGuard()

    mapped = {word for senses in base.values() for word, _ in senses}
    key_rows: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    for filename in RUNTIME_EXPANSIONS:
        path = DATA / filename
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            chinese, word, pos, _source = line.split("\t")
            mapped.add(word)
            key_rows[chinese].append((word, pos))
    extra_count = collections.Counter({key: len(rows) for key, rows in key_rows.items()})
    missing = {word for word, mask in tags.items() if mask and word not in mapped and WORD.fullmatch(word)}
    missing_targets = {
        target: {word for word in missing if tags[word] & (1 << TARGET_BITS[target])}
        for target in TARGETS
    }

    pos_synsets: dict[tuple[str, str], set[tuple[str, str]]] = collections.defaultdict(set)
    for (pos, word), synsets in guard.lemmas.items():
        pos_synsets[(pos, word)].update((syn_pos, offset) for syn_pos, offset in synsets if syn_pos == pos)

    candidates: dict[tuple[str, str, str], dict[str, str]] = {}
    missing_pinyin: dict[tuple[str, str, str], dict[str, str]] = {}
    rejected = collections.Counter()
    entries_read = 0
    offset = 0
    while offset < len(idx):
        end = idx.index(b"\0", offset)
        word = idx[offset:end].decode("utf-8", "replace").casefold()
        entry_offset, size = struct.unpack(">II", idx[end + 1:end + 9])
        offset = end + 9
        if word not in missing:
            continue
        if word not in ipa:
            rejected["missing_ipa"] += 1
            continue
        entries_read += 1
        raw = dictionary[entry_offset:entry_offset + size].decode("utf-8", "replace")
        for pos, chinese, source_rank, context in parse_entry(raw):
            mask = tags[word]
            matched_targets = [target for target in TARGETS if mask & (1 << TARGET_BITS[target])]
            evidence = f"[{pos}] {context}"
            if chinese not in pinyin:
                rejected["no_current_pinyin_key"] += 1
                exact_cow = any(chinese in cow.get((syn_pos, synset_offset), set())
                                for syn_pos, synset_offset in pos_synsets.get((pos.rstrip("."), word), set()))
                pair = (word, chinese, pos)
                row = missing_pinyin.get(pair)
                if row is None:
                    missing_pinyin[pair] = {
                        "word": word,
                        "chinese": chinese,
                        "pos": pos,
                        "targets": ",".join(matched_targets),
                        "source_rank": str(source_rank),
                        "exact_cow_synset": "yes" if exact_cow else "no",
                        "source_evidence": evidence,
                    }
                else:
                    row["source_rank"] = str(min(int(row["source_rank"]), source_rank))
                    if exact_cow:
                        row["exact_cow_synset"] = "yes"
                    if evidence not in row["source_evidence"]:
                        row["source_evidence"] += " || " + evidence
                continue
            if extra_count[chinese] >= 8:
                rejected["runtime_key_capacity_full"] += 1
                continue
            exact_cow = any(chinese in cow.get((syn_pos, synset_offset), set())
                            for syn_pos, synset_offset in pos_synsets.get((pos.rstrip("."), word), set()))
            base_pos = pos in {sense_pos for _, sense_pos in base.get(chinese, [])}
            related = bool(base_pos and guard.synsets(word, pos)
                           and guard.related(word, pos, base.get(chinese, [])))
            pair = (word, chinese, pos)
            existing = candidates.get(pair)
            if existing:
                existing["source_rank"] = str(min(int(existing["source_rank"]), source_rank))
                if evidence not in existing["source_evidence"]:
                    existing["source_evidence"] += " || " + evidence
                existing["exact_cow_synset"] = "yes" if exact_cow else existing["exact_cow_synset"]
                existing["wordnet_related_to_base"] = "yes" if related else existing["wordnet_related_to_base"]
                continue
            candidates[pair] = {
                "word": word,
                "chinese": chinese,
                "pos": pos,
                "targets": ",".join(matched_targets),
                "source_rank": str(source_rank),
                "pinyin": pinyin[chinese][0],
                "pinyin_frequency": str(pinyin[chinese][1]),
                "exact_cow_synset": "yes" if exact_cow else "no",
                "packed_gloss_key": "yes" if chinese in base else "no",
                "base_pos_match": "yes" if base_pos else "no",
                "wordnet_related_to_base": "yes" if related else "no",
                "source_evidence": evidence,
                "base_senses": " | ".join(f"{sense} [{sense_pos}]" for sense, sense_pos in base.get(chinese, [])),
                "runtime_key_count": str(extra_count[chinese]),
            }

    ordered = sorted(candidates.values(), key=lambda row: (
        -int(row["exact_cow_synset"] == "yes"),
        -int(row["wordnet_related_to_base"] == "yes"),
        -int(row["base_pos_match"] == "yes"),
        int(row["source_rank"]),
        -len(row["targets"].split(",")),
        -int(row["pinyin_frequency"]),
        row["word"], row["chinese"], row["pos"],
    ))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    headers = (
        "word", "chinese", "pos", "targets", "pinyin", "pinyin_frequency",
        "source_rank",
        "exact_cow_synset", "packed_gloss_key", "base_pos_match", "wordnet_related_to_base",
        "source_evidence", "base_senses", "runtime_key_count",
    )
    with OUTPUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(ordered)

    missing_ordered = sorted(missing_pinyin.values(), key=lambda row: (
        int(row["source_rank"]), -len(row["targets"].split(",")), row["word"], row["chinese"], row["pos"],
    ))
    missing_output = OUTPUT.with_name("koreader-v1.2.0-missing-pinyin.tsv")
    with missing_output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("word", "chinese", "pos", "targets", "source_rank", "exact_cow_synset", "source_evidence"), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(missing_ordered)

    summary = {
        "source": "DanielGregorini/koreader-dicts English-Chinese StarDict v1.2.0",
        "release_url": "https://github.com/DanielGregorini/koreader-dicts/releases/tag/v1.2.0",
        "archive_sha256": ARCHIVE_SHA256,
        "license": "CC BY-SA 4.0 compilation; component notices in upstream ATTRIBUTION",
        "cow_source_sha256": COW_SOURCE_SHA256,
        "missing_headwords_before_review": {target: len(words) for target, words in missing_targets.items()},
        "source_entries_with_ipa": entries_read,
        "candidate_pairs": len(ordered),
        "candidate_headwords": len({row["word"] for row in ordered}),
        "missing_pinyin_candidate_pairs": len(missing_ordered),
        "missing_pinyin_candidate_headwords": len({row["word"] for row in missing_ordered}),
        "missing_pinyin_candidate_headwords_by_target": {
            target: len({row["word"] for row in missing_ordered if target in row["targets"].split(",")})
            for target in TARGETS
        },
        "missing_pinyin_exact_cow_headwords_by_target": {
            target: len({row["word"] for row in missing_ordered
                         if target in row["targets"].split(",") and row["exact_cow_synset"] == "yes"})
            for target in TARGETS
        },
        "candidate_headwords_by_target": {
            target: len({row["word"] for row in ordered if target in row["targets"].split(",")})
            for target in TARGETS
        },
        "candidate_headwords_by_target_and_evidence": {
            target: {
                evidence: len({row["word"] for row in ordered
                               if target in row["targets"].split(",") and row[evidence_column] == "yes"})
                for evidence, evidence_column in (
                    ("exact_cow_synset", "exact_cow_synset"),
                    ("wordnet_related_to_base", "wordnet_related_to_base"),
                    ("base_pos_match", "base_pos_match"),
                )
            }
            for target in TARGETS
        },
        "rejected": dict(sorted(rejected.items())),
        "selection_rule": "Review-only: exact tagged missing headword, exact existing pinyin key, bundled IPA, upstream POS-tagged gloss, runtime key below 8. COW synset and base WordNet/POS matches are confidence evidence; no row is adopted automatically.",
        "limitations": "The compiled dictionary combines Open Wordnet/WordNet and Wiktionary senses; a dictionary gloss can still be unsuitable for a particular learner sense. Source context is retained for manual review.",
        "output_sha256": sha(OUTPUT),
        "missing_pinyin_output_sha256": sha(missing_output),
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
