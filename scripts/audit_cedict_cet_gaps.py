"""Generate a review-only queue from a pinned CC-CEDICT snapshot.

CC-CEDICT is Chinese-to-English and has no part-of-speech tags. This script
only proposes a candidate when one complete English definition is exactly a
currently unmapped CET4/CET6 headword (or ``to <headword>``), and the
simplified Chinese headword is already a 2-6 Han-character Qingjian glossary
key and an exact packed pinyin candidate. The TSV is for manual review only.
It never changes the shipped vocabulary.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
import urllib.request
from pathlib import Path

from prepare_cet_batch import DATA, ROOT, load_base
from prepare_candidate_batch import parse_pinyin_candidates


PINNED_REPO = "TeaPearce/chinese-english-dictionary"
PINNED_COMMIT = "a9aea223269eb9820590e5bca783eb299c317439"
PINNED_PATH = "data/cedict_ts_june2026.u8"
PINNED_SHA256 = "8172061b2a647dd8a179788830ef233944baee479bc7018f111064ad16d8f46f"
PINNED_URL = (
    f"https://raw.githubusercontent.com/{PINNED_REPO}/"
    f"{PINNED_COMMIT}/{PINNED_PATH}"
)
DEFAULT_SOURCE = ROOT / "build/source-audit/cc-cedict/cedict_ts_june2026.u8"
OUT = ROOT / "build/source-audit/cc-cedict"
HAN = re.compile(r"[\u4e00-\u9fff]{2,6}")
ENTRY = re.compile(r"^(\S+)\s+(\S+)\s+\[([^]]+)\]\s+/(.*)/\s*$")
POS_PREFIX = re.compile(r"^([a-z]+)\.\s*(.*)$")
POS_MAP = {
    "n": "n.", "v": "v.", "vt": "v.", "vi": "v.",
    "a": "adj.", "adj": "adj.", "adv": "adv.",
    "pron": "pron.", "prep": "prep.", "conj": "conj.", "num": "num.",
    "m": "m.", "mw": "m.", "part": "part.", "int": "int.",
    "interj": "int.", "phr": "phr.", "phrase": "phr.",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_ipa() -> set[str]:
    result = set()
    for name in ("en_UK.txt", "en_US.txt"):
        for line in (ROOT / "pronunciation/source" / name).read_text(encoding="utf-8").splitlines():
            if "\t" in line:
                result.add(line.split("\t", 1)[0].strip().lower())
    return result


def load_current_words(base: dict[str, list[tuple[str, str]]]) -> set[str]:
    words = {word for senses in base.values() for word, _ in senses}
    for name in ("english-expansion.tsv", "wiktionary-expansion.tsv"):
        path = DATA / name
        for line in path.read_text(encoding="utf-8").splitlines():
            chinese, word, _pos, _source = line.split("\t")
            words.add(word)
    return words


def load_ecdict() -> dict[str, dict[str, str]]:
    path = ROOT / "build/vocabulary-research/skywind3000__ECDICT/ecdict.csv"
    meta = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    expected = next(row["sha256"] for row in meta["input_files"] if row["path"] == "ecdict.csv")
    actual = sha(path)
    if actual != expected:
        raise ValueError(f"Pinned ECDICT checksum mismatch: {actual}")
    result = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            word = row["word"].strip().lower()
            if not word:
                continue
            pos = []
            for line in row.get("translation", "").replace("\\n", "\n").splitlines():
                match = POS_PREFIX.match(line.strip())
                if match and match.group(1) in POS_MAP:
                    pos.append((POS_MAP[match.group(1)], match.group(2).strip()))
            result[word] = {
                "translation": row.get("translation", "").replace("\n", r"\n").strip(),
                "pos": " | ".join(f"{kind} {gloss}" for kind, gloss in pos),
            }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--download", action="store_true", help="download the pinned CC-CEDICT mirror into the ignored build cache")
    args = parser.parse_args()
    if not args.source.is_file():
        if not args.download:
            raise SystemExit(f"Missing pinned CC-CEDICT snapshot: {args.source}; rerun with --download")
        args.source.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(PINNED_URL, args.source)
    if sha(args.source) != PINNED_SHA256:
        raise SystemExit(f"Pinned CC-CEDICT checksum mismatch: {args.source}")

    tags = {
        word: int(first) | int(second)
        for word, first, second in (
            line.split("\t") for line in (DATA / "english-tags.tsv").read_text(encoding="utf-8").splitlines()
        )
    }
    base = load_base(ROOT / "build/expansion-base.tsv")
    current = load_current_words(base)
    missing = {
        word: mask for word, mask in tags.items()
        if mask & 0b11 and word not in current
    }
    pinyin = parse_pinyin_candidates(ROOT / "build/pinyin-candidates.tsv")
    ipa = load_ipa()
    ecdict = load_ecdict()

    matches: dict[tuple[str, str, str], dict[str, str]] = {}
    parsed_lines = 0
    for line_number, line in enumerate(args.source.read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        match = ENTRY.fullmatch(line)
        if not match:
            continue
        parsed_lines += 1
        traditional, simplified, cedict_pinyin, raw_definitions = match.groups()
        if not HAN.fullmatch(simplified) or simplified not in pinyin or simplified not in base:
            continue
        for definition in raw_definitions.split("/"):
            gloss = definition.strip().lower()
            if not gloss:
                continue
            for word in missing:
                if word not in ecdict or word not in ipa:
                    continue
                if gloss == word:
                    match_kind = "exact"
                elif gloss == "to " + word:
                    match_kind = "to-verb"
                else:
                    continue
                row = {
                    "word": word,
                    "targets": ",".join(
                        code for bit, code in enumerate(("cet4", "cet6"))
                        if missing[word] & (1 << bit)
                    ),
                    "pos": ecdict[word]["pos"],
                    "chinese": simplified,
                    "pinyin": pinyin[simplified][0],
                    "pinyin_frequency": str(pinyin[simplified][1]),
                    "match_kind": match_kind,
                    "english_gloss": gloss,
                    "cedict_pinyin": cedict_pinyin,
                    "traditional": traditional,
                    "source_line": str(line_number),
                    "base_senses": " | ".join(f"{pos} {english}" for english, pos in base[simplified]),
                    "ecdict_translation": ecdict[word]["translation"],
                }
                matches[(word, simplified, match_kind)] = row

    columns = (
        "word", "targets", "pos", "chinese", "pinyin", "pinyin_frequency",
        "match_kind", "english_gloss", "cedict_pinyin", "traditional",
        "source_line", "base_senses", "ecdict_translation",
    )
    ordered = sorted(matches.values(), key=lambda row: (
        -int(row["pinyin_frequency"]), row["word"], row["chinese"], row["match_kind"]
    ))
    OUT.mkdir(parents=True, exist_ok=True)
    tsv = "\t".join(columns) + "\n" + "".join(
        "\t".join(row[column].replace("\t", " ").replace("\n", " ") for column in columns) + "\n"
        for row in ordered
    )
    (OUT / "cet-pinyin-candidates.tsv").write_text(tsv, encoding="utf-8", newline="\n")
    summary = {
        "batch": "02-cc-cedict-audit-1",
        "source": {
            "project": "CC-CEDICT",
            "publisher": "MDBG",
            "license": "CC BY-SA 4.0",
            "official_license_and_download": "https://cc-cedict.org/editor/editor.php?handler=Download",
            "source_snapshot_description": "June 2026 raw CC-CEDICT file mirrored with attribution in TeaPearce/chinese-english-dictionary",
            "mirror_repo": f"https://github.com/{PINNED_REPO}",
            "mirror_commit": PINNED_COMMIT,
            "path": PINNED_PATH,
            "url": PINNED_URL,
            "sha256": sha(args.source),
            "bytes": args.source.stat().st_size,
        },
        "pinned_ecdict_sha256": sha(ROOT / "build/vocabulary-research/skywind3000__ECDICT/ecdict.csv"),
        "pinned_tag_sha256": sha(DATA / "english-tags.tsv"),
        "pinyin_candidates_sha256": sha(ROOT / "build/pinyin-candidates.tsv"),
        "candidate_tsv_sha256": sha(OUT / "cet-pinyin-candidates.tsv"),
        "parsed_cedict_entries": parsed_lines,
        "unmapped_cet4_cet6_words_before_review": len(missing),
        "candidate_rows": len(ordered),
        "candidate_unique_words": len({row["word"] for row in ordered}),
        "candidate_chinese_keys": len({row["chinese"] for row in ordered}),
        "candidate_rule": "Exact whole CC-CEDICT English gloss only (headword or 'to headword'); require CET tags, bundled IPA, exact simplified Qingjian pinyin key, and existing packed glossary key. CC-CEDICT supplies no POS; candidate POS shown here comes from pinned ECDICT and must be manually reviewed against the exact English gloss.",
        "disclaimer": "Review queue only. It does not change runtime data; every adopted pair needs human sense/POS review and separate CC BY-SA 4.0 attribution.",
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
