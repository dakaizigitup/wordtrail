"""Select the next exam-vocabulary tranche from pinned, reviewable source queues.

This is a build-time audit tool. It writes one selected mapping per previously
unmapped exam headword, a row-level evidence ledger, and a low-priority pinyin
overlay. Runtime code loads only the small generated TSV indexes.
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
OUT_DIR = ROOT / "build/source-audit/exam-targets"
REVIEWED = DATA / "batches/11-exam-target-reviewed.tsv"
Pinyin_OUT = DATA / "pinyin-overlays/exam-target-batch-11.tsv"
MANIFEST_OUT = DATA / "exam-target-batch-11-manifest.json"
TARGETS = ("cet4", "cet6", "tem4", "tem8", "toefl", "ielts")
BITS = {target: bit for bit, target in enumerate(TARGETS)}
HAN = re.compile(r"[\u3400-\u9fff]{2,6}\Z")
WORD = re.compile(r"[a-z]+(?:[-'][a-z]+)*\Z")
POS_RANK = {"n.": 0, "v.": 1, "adj.": 2, "adv.": 3}
OUTPUT_FILES = {
    "ECDICT MIT": DATA / "exam-target-batch-11-ecdict-expansion.tsv",
    "KyleBing BSD-3-Clause": DATA / "exam-target-batch-11-kylebing-expansion.tsv",
    "ECDICT MIT + KyleBing BSD-3-Clause": DATA / "exam-target-batch-11-dual-expansion.tsv",
    "Chinese Open Wordnet": DATA / "exam-target-batch-11-cow-expansion.tsv",
    "KOReader dictionaries CC BY-SA 4.0 + Chinese Open Wordnet": DATA / "exam-target-batch-11-koreader-cow-expansion.tsv",
    "CC BY-SA 4.0": DATA / "exam-target-batch-11-cc-by-sa-expansion.tsv",
}
# Later tranches are intentionally excluded when rebuilding the frozen batch 11
# baseline; each tranche is selected against only the data that preceded it.
GENERATED_NAMES = {path.name for path in OUTPUT_FILES.values()} | {
    "exam-target-batch-12-ecdict-expansion.tsv",
}
CEDICT_PATH = BUILD / "cc-cedict/cedict_ts_june2026.u8"
RIME_ROOT = BUILD / "rime-ice/da1fbe602e38f26db846fa10120ee64c2b0324c0/cn_dicts"
FMLD_PATH = OUT_DIR / "fmld-candidates-new-key.tsv"
KO_PATH = OUT_DIR / "koreader-v1.2.0-candidates.tsv"
KO_MISSING_PATH = OUT_DIR / "koreader-v1.2.0-missing-pinyin.tsv"
OPEN_DICT_PATH = OUT_DIR / "open-dictionary-v2-candidates.tsv"
DUAL_PATH = OUT_DIR / "candidate-review.tsv"
COW_PATH = OUT_DIR / "cow-candidates.tsv"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def input_hash(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"Missing pinned audit input: {path}")
    return sha(path)


def load_context():
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.path.insert(0, str(ROOT / "build/vocab-tools"))
    from audit_cedict_cet_gaps import DEFAULT_SOURCE, ENTRY, POS_PREFIX, POS_MAP, load_ecdict, sha as audit_sha
    from exam_targets import RUNTIME_EXPANSIONS, load_exam_tags
    from prepare_candidate_batch import parse_pinyin_candidates
    from prepare_cet_batch import coverage, load_base
    from opencc import OpenCC

    if audit_sha(DEFAULT_SOURCE) != "8172061b2a647dd8a179788830ef233944baee479bc7018f111064ad16d8f46f":
        raise SystemExit("Pinned CC-CEDICT snapshot checksum mismatch")
    converter = OpenCC("t2s")
    base = load_base(ROOT / "build/expansion-base.tsv")
    current_pinyin = parse_pinyin_candidates(ROOT / "build/pinyin-candidates.tsv")
    tags = load_exam_tags(DATA)
    ipa = {
        line.split("\t", 1)[0].strip().casefold()
        for name in ("en_UK.txt", "en_US.txt")
        for line in (ROOT / "pronunciation/source" / name).read_text(encoding="utf-8").splitlines()
        if "\t" in line
    }
    mapped = {word for senses in base.values() for word, _ in senses}
    extras: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    for filename in RUNTIME_EXPANSIONS:
        if filename in GENERATED_NAMES:
            continue
        path = DATA / filename
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            chinese, word, pos, _source = line.split("\t")
            mapped.add(word)
            extras[chinese].append((word, pos))
    ecdict = load_ecdict()
    ecdict_pos_gloss: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for word, row in ecdict.items():
        for raw in row["translation"].replace(r"\n", "\n").splitlines():
            match = POS_PREFIX.match(raw.strip())
            if not match or match[1] not in POS_MAP:
                continue
            pos = POS_MAP[match[1]]
            for gloss in re.split(r"[,，;；]", match[2]):
                chinese = gloss.strip()
                if HAN.fullmatch(chinese):
                    ecdict_pos_gloss[(word, chinese)].add(pos)

    cedict_readings: dict[str, set[str]] = collections.defaultdict(set)
    for line in DEFAULT_SOURCE.read_text(encoding="utf-8").splitlines():
        match = ENTRY.fullmatch(line)
        if not match:
            continue
        _traditional, simplified, raw_pinyin, _definitions = match.groups()
        simplified = converter.convert(simplified)
        if HAN.fullmatch(simplified):
            cedict_readings[simplified].add(normalize_cedict_pinyin(raw_pinyin))

    rime_readings: dict[str, set[str]] = collections.defaultdict(set)
    rime_hashes = {}
    for filename in ("base.dict.yaml", "ext.dict.yaml"):
        path = RIME_ROOT / filename
        rime_hashes[filename] = input_hash(path)
        in_dictionary = False
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip() == "---":
                in_dictionary = True
                continue
            if not in_dictionary or not raw or raw.startswith("#"):
                continue
            fields = raw.split("\t")
            if len(fields) < 2:
                continue
            chinese = converter.convert(fields[0].strip())
            reading = " ".join(fields[1].split()).casefold()
            if HAN.fullmatch(chinese) and re.fullmatch(r"[a-zv]+(?: [a-zv]+)*", reading):
                rime_readings[chinese].add(reading)

    return {
        "ENTRY": ENTRY, "DEFAULT_SOURCE": DEFAULT_SOURCE, "converter": converter,
        "base": base, "current_pinyin": current_pinyin, "tags": tags, "ipa": ipa,
        "mapped": mapped, "extras": extras, "ecdict": ecdict,
        "ecdict_pos_gloss": ecdict_pos_gloss, "cedict_readings": cedict_readings,
        "rime_readings": rime_readings, "rime_hashes": rime_hashes,
        "coverage": coverage, "runtime_files": RUNTIME_EXPANSIONS,
    }


def normalize_cedict_pinyin(value: str) -> str:
    value = value.replace("u:", "v").replace("ü", "v").replace("Ü", "v")
    syllables = [re.sub(r"[1-5]", "", item).casefold() for item in value.split()]
    return " ".join(syllables)


def resolve_unmapped_pinyin(chinese: str, ctx: dict) -> tuple[str, str] | None:
    if chinese in ctx["current_pinyin"]:
        return ctx["current_pinyin"][chinese][0], "Qingjian v0.1.4"
    cedict = ctx["cedict_readings"].get(chinese, set())
    rime = ctx["rime_readings"].get(chinese, set())
    if len(cedict) == 1 and len(rime) == 1:
        if cedict != rime:
            return None
        return next(iter(cedict)), "CC-CEDICT CC BY-SA 4.0 + Rime ICE GPL-3.0"
    if len(cedict) == 1 and not rime:
        return next(iter(cedict)), "CC-CEDICT CC BY-SA 4.0"
    if len(rime) == 1 and not cedict:
        return next(iter(rime)), "Rime ICE GPL-3.0"
    if len(cedict) == 1 and cedict <= rime:
        return next(iter(cedict)), "CC-CEDICT CC BY-SA 4.0"
    if len(rime) == 1 and rime <= cedict:
        return next(iter(rime)), "Rime ICE GPL-3.0"
    return None


def candidate(word: str, chinese: str, pos: str, source: str, source_ref: str,
              pinyin: str, pinyin_source: str, confidence: str, evidence: str,
              target_mask: int, priority: int, frequency: int = 0) -> dict:
    return {
        "word": word, "chinese": chinese, "pos": pos,
        "targets": ",".join(t for t in TARGETS if target_mask & (1 << BITS[t])),
        "source": source, "source_reference": source_ref,
        "pinyin": pinyin, "pinyin_source": pinyin_source,
        "pinyin_frequency": str(frequency), "confidence": confidence,
        "evidence": evidence.replace("\t", " ").replace("\r", " ").replace("\n", r"\n"),
        "priority": priority,
    }


def load_candidates(ctx: dict) -> tuple[list[dict], collections.Counter]:
    rows: list[dict] = []
    rejected = collections.Counter()
    tags, ipa, mapped = ctx["tags"], ctx["ipa"], ctx["mapped"]
    current_pinyin = ctx["current_pinyin"]
    ecdict = ctx["ecdict"]

    def add(row: dict) -> None:
        word = row["word"].casefold()
        chinese = ctx["converter"].convert(row["chinese"]).strip()
        pos = row["pos"].strip()
        if not WORD.fullmatch(word):
            rejected["invalid_headword"] += 1; return
        if word in mapped:
            rejected["already_mapped"] += 1; return
        if word not in tags or not (tags[word] & 0b111100):
            rejected["not_a_target_headword"] += 1; return
        if word not in ipa:
            rejected["missing_ipa"] += 1; return
        if pos not in POS_RANK:
            rejected["unsupported_pos"] += 1; return
        if not HAN.fullmatch(chinese):
            rejected["invalid_chinese_gloss"] += 1; return
        resolved = row.get("pinyin_result") or resolve_unmapped_pinyin(chinese, ctx)
        if not resolved:
            rejected["unverified_pinyin"] += 1; return
        pinyin, pinyin_source = resolved
        if not re.fullmatch(r"[a-zv]+(?: [a-zv]+)*", pinyin):
            rejected["invalid_pinyin"] += 1; return
        if chinese in current_pinyin:
            pinyin = current_pinyin[chinese][0]
            pinyin_source = "Qingjian v0.1.4"
        if chinese not in ctx["base"] and chinese not in current_pinyin and row.get("pinyin_result") is None:
            rejected["new_key_without_source_reading"] += 1; return
        out = candidate(word, chinese, pos, row["source"], row["source_reference"],
                        pinyin, pinyin_source, row["confidence"], row["evidence"], tags[word],
                        row["priority"], int(row.get("pinyin_frequency") or 0))
        rows.append(out)

    # Agreement between ECDICT and the exam-specific KyleBing list, plus
    # single-source whole-gloss candidates, all have a direct lexical source.
    for number, row in enumerate(tsv(OUT_DIR / "candidate-review.tsv"), 2):
        ecdict_yes = row["ecdict_exact_pos_gloss"] == "yes"
        kyle_yes = row["kyle_exact_pos_gloss"] == "yes"
        if not ecdict_yes and not kyle_yes:
            continue
        source = ("ECDICT MIT + KyleBing BSD-3-Clause" if ecdict_yes and kyle_yes
                  else "ECDICT MIT" if ecdict_yes else "KyleBing BSD-3-Clause")
        pinyin = row["pinyin"]
        if row["chinese"] not in current_pinyin:
            rejected["source_candidate_pinyin_key_missing"] += 1; continue
        add({**row, "source": source, "source_reference": f"candidate-review.tsv:{number}",
             "pinyin_result": (pinyin, "Qingjian v0.1.4"), "confidence": "exact complete source gloss",
             "evidence": "ECDICT exact POS gloss=" + row["ecdict_exact_pos_gloss"] +
                         "; KyleBing exact POS gloss=" + row["kyle_exact_pos_gloss"] +
                         "; exam-list source=" + row["kyle_sources"],
             "priority": 0 if ecdict_yes and kyle_yes else 1,
             "pinyin_frequency": row["pinyin_frequency"]})

    # Exact English/Chinese WordNet synset candidates.
    for number, row in enumerate(tsv(COW_PATH), 2):
        if row["chinese"] not in current_pinyin:
            rejected["cow_source_key_missing"] += 1; continue
        add({**row, "source": "Chinese Open Wordnet", "source_reference":
             f"{row['synset_pos']}:{row['synset_offset']}", "pinyin_result":
             (row["pinyin"], "Qingjian v0.1.4"), "confidence": "exact English/Chinese synset",
             "evidence": "same WordNet synset; same POS; current Chinese candidate key",
             "priority": 1, "pinyin_frequency": row["pinyin_frequency"]})

    # Pinned FMLD dictionary: an entire English gloss equals the target term.
    for number, row in enumerate(tsv(FMLD_PATH), 2):
        if row["base_pos_match"] != "yes":
            rejected["fmld_pos_mismatch"] += 1; continue
        glosses = {part.strip().casefold().strip(" .,:;!?()[]{}\"'")
                   for part in row["english_gloss"].split(";")}
        if not glosses.intersection({row["word"], "to " + row["word"]}):
            rejected["fmld_gloss_not_exact"] += 1; continue
        add({**row, "source": "FMLD CC BY-SA 4.0", "source_reference":
             f"{row['source_definition_id']} / line {row['source_line']}",
             "pinyin_result": (row["pinyin"], "Qingjian v0.1.4"),
             "confidence": "exact complete FMLD gloss; matching POS",
             "evidence": row["english_gloss"], "priority": 1,
             "pinyin_frequency": row["pinyin_frequency"]})

    # KOReader's first exact gloss or a direct COW synset match. The latter is
    # allowed at any source position because it independently resolves sense.
    for number, row in enumerate(tsv(KO_PATH), 2):
        exact_cow = row["exact_cow_synset"] == "yes"
        first_sense_supported = (row["source_rank"] in {"1", "2"} and
                                 row["base_pos_match"] == "yes" and
                                 row["wordnet_related_to_base"] == "yes")
        if not exact_cow and not first_sense_supported:
            rejected["koreader_sense_not_corroborated"] += 1; continue
        add({**row, "source": "KOReader dictionaries CC BY-SA 4.0", "source_reference":
             f"en-zh v1.2.0 source rank {row['source_rank']}",
             "pinyin_result": (row["pinyin"], "Qingjian v0.1.4"),
             "confidence": "exact COW synset" if exact_cow else "first gloss; matching POS and WordNet relation",
             "evidence": f"source rank {row['source_rank']}; COW synset={row['exact_cow_synset']}; WordNet related={row['wordnet_related_to_base']}", "priority": 2,
             "pinyin_frequency": row["pinyin_frequency"]})

    # New pinyin keys from the KOReader table are only accepted when the
    # candidate shares an exact Chinese Open Wordnet synset with the English.
    for number, row in enumerate(tsv(KO_MISSING_PATH), 2):
        if row["exact_cow_synset"] != "yes":
            rejected["koreader_new_key_without_exact_synset"] += 1; continue
        chinese = ctx["converter"].convert(row["chinese"]).strip()
        resolved = resolve_unmapped_pinyin(chinese, ctx)
        if not resolved:
            rejected["koreader_new_key_unverified_pinyin"] += 1; continue
        add({**row, "chinese": chinese, "source": "KOReader dictionaries CC BY-SA 4.0 + Chinese Open Wordnet",
             "source_reference": f"en-zh v1.2.0 rank {row['source_rank']}; exact COW synset",
             "pinyin_result": resolved, "confidence": "exact COW synset; independent pinyin dictionary agreement",
             "evidence": "exact English/Chinese Open Wordnet synset; pinyin resolved independently",
             "priority": 1,
             "pinyin_frequency": "0"})

    # CC-CEDICT contains complete English glosses and its own pronunciation.
    # POS comes from the separately pinned ECDICT record; exact POS/gloss
    # agreement is recorded when that source has the same Chinese short gloss.
    target_words = {word for word, mask in ctx["tags"].items()
                    if word not in mapped and mask & 0b111100 and word in ipa}
    gloss_map: dict[str, set[str]] = collections.defaultdict(set)
    for word in target_words:
        gloss_map[word].add(word)
        if word in ipa:
            gloss_map["to " + word].add(word)
    for line_number, line in enumerate(ctx["DEFAULT_SOURCE"].read_text(encoding="utf-8").splitlines(), 1):
        match = ctx["ENTRY"].fullmatch(line)
        if not match:
            continue
        _traditional, simplified, raw_pinyin, definitions = match.groups()
        simplified = ctx["converter"].convert(simplified).strip()
        if not HAN.fullmatch(simplified):
            continue
        source_pinyin = normalize_cedict_pinyin(raw_pinyin)
        for definition in definitions.split("/"):
            gloss = definition.strip().casefold()
            for word in gloss_map.get(gloss, ()):
                pos_set = set(ecdict_pos(word))
                if gloss.startswith("to "):
                    pos = "v." if "v." in pos_set else ""
                else:
                    exact_pos = ctx["ecdict_pos_gloss"].get((word, simplified), set())
                    pos = next((p for p in sorted(exact_pos, key=lambda p: POS_RANK.get(p, 99)) if p in POS_RANK), "")
                    if not pos:
                        pos = next((p for p in ecdict_pos(word) if p in POS_RANK), "")
                if not pos:
                    rejected["cedict_missing_pos"] += 1; continue
                if simplified in current_pinyin:
                    resolved = (current_pinyin[simplified][0], "Qingjian v0.1.4")
                    frequency = str(current_pinyin[simplified][1])
                else:
                    resolved = (source_pinyin, "CC-CEDICT CC BY-SA 4.0")
                    frequency = "0"
                add({"word": word, "chinese": simplified, "pos": pos,
                     "source": "CC-CEDICT CC BY-SA 4.0",
                     "source_reference": f"2026-06 CC-CEDICT line {line_number}",
                     "pinyin_result": resolved, "confidence":
                     "exact complete CC-CEDICT gloss; POS from ECDICT",
                     "evidence": gloss, "priority": 2 if (word, simplified) not in ctx["ecdict_pos_gloss"] else 1,
                     "pinyin_frequency": frequency})

    # Open Dictionary's core/common learner glosses are LLM-assisted; retain a
    # row only when the same POS and Chinese gloss also occur in pinned ECDICT.
    for number, row in enumerate(tsv(OPEN_DICT_PATH), 2):
        if row["priority"] not in {"core", "common"}:
            continue
        chinese, word, pos = row["chinese"], row["word"], row["pos"]
        if pos not in ctx["ecdict_pos_gloss"].get((word, chinese), set()):
            rejected["open_dictionary_not_crosschecked"] += 1; continue
        add({**row, "source": "Open Dictionary v2 CC BY-SA 4.0 + ECDICT MIT",
             "source_reference": f"sense {row['source_sense_id']}",
             "pinyin_result": (row["pinyin"], "Qingjian v0.1.4"),
             "confidence": "core/common gloss; ECDICT exact POS gloss cross-check",
             "evidence": row["source_learner_explanation"], "priority": 1,
             "pinyin_frequency": row["pinyin_frequency"]})

    # Keep one mapping per new English headword. Prefer stronger sources,
    # existing pinyin keys, and then the most common pinyin candidate.
    by_word: dict[str, list[dict]] = collections.defaultdict(list)
    for row in rows:
        by_word[row["word"]].append(row)
    for word in by_word:
        unique = {}
        for row in by_word[word]:
            key = (row["chinese"], row["pos"], row["source"])
            old = unique.get(key)
            rank = (row["priority"], row["pinyin_source"] != "Qingjian v0.1.4",
                    -int(row["pinyin_frequency"]), row["chinese"])
            if old is None or rank < old[0]:
                unique[key] = (rank, row)
        by_word[word] = [item[1] for item in unique.values()]

    selected: list[dict] = []
    used_words = set()
    cap = collections.Counter({chinese: len(records) for chinese, records in ctx["extras"].items()})
    for word in sorted(by_word, key=lambda w: (
        min(row["priority"] for row in by_word[w]),
        -sum(1 for t in TARGETS[2:] if ctx["tags"][w] & (1 << BITS[t])),
        w,
    )):
        choices = sorted(by_word[word], key=lambda row: (
            row["priority"], row["pinyin_source"] != "Qingjian v0.1.4",
            -int(row["pinyin_frequency"]), row["chinese"], row["source"],
        ))
        for row in choices:
            if cap[row["chinese"]] >= 8:
                rejected["per_chinese_key_capacity"] += 1
                continue
            selected.append(row); used_words.add(word); cap[row["chinese"]] += 1
            break
    return selected, rejected


def ecdict_pos(word: str) -> list[str]:
    from audit_cedict_cet_gaps import POS_PREFIX, POS_MAP
    path = ROOT / "build/vocabulary-research/skywind3000__ECDICT/ecdict.csv"
    # The caller preloads the compact ECDICT index; this helper is filled by
    # the module-level cache below to avoid rescanning the 65 MB CSV.
    return ECDICT_POS.get(word, [])


ECDICT_POS: dict[str, list[str]] = {}


def fill_ecdict_pos() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from audit_cedict_cet_gaps import POS_PREFIX, POS_MAP, load_ecdict
    for word, row in load_ecdict().items():
        positions = []
        for line in row["translation"].replace(r"\n", "\n").splitlines():
            match = POS_PREFIX.match(line.strip())
            if match and match[1] in POS_MAP and POS_MAP[match[1]] in POS_RANK:
                pos = POS_MAP[match[1]]
                if pos not in positions:
                    positions.append(pos)
        ECDICT_POS[word] = positions


def make_review_payload(rows: list[dict]) -> str:
    headers = ("word", "chinese", "pos", "targets", "source", "source_reference",
               "pinyin", "pinyin_source", "pinyin_frequency", "confidence", "evidence")
    return "\t".join(headers) + "\n" + "".join(
        "\t".join(str(row[h]).replace("\t", " ").replace("\n", r"\n") for h in headers) + "\n"
        for row in rows)


def output_group(source: str) -> str:
    if source in OUTPUT_FILES:
        return source
    if source.startswith("ECDICT MIT + KyleBing BSD-3-Clause"):
        return "ECDICT MIT + KyleBing BSD-3-Clause"
    if source.startswith("ECDICT MIT"):
        return "ECDICT MIT"
    if source.startswith("KyleBing BSD-3-Clause"):
        return "KyleBing BSD-3-Clause"
    if source.startswith("Chinese Open Wordnet"):
        return "Chinese Open Wordnet"
    return "CC BY-SA 4.0"


def expansion_payloads(rows: list[dict]) -> dict[Path, str]:
    groups: dict[str, list[dict]] = collections.defaultdict(list)
    for row in rows:
        groups[output_group(row["source"])].append(row)
    payloads = {}
    for group, path in OUTPUT_FILES.items():
        selected = sorted(groups.get(group, []), key=lambda row: (row["chinese"], row["word"], row["pos"]))
        payloads[path] = "".join(
            f"{row['chinese']}\t{row['word']}\t{row['pos']}\t{row['source']}\n"
            for row in selected)
    return payloads


def make_manifest(rows: list[dict], rejected: collections.Counter, ctx: dict,
                  review_payload: str, overlay_payload: str,
                  expansion_payload_map: dict[Path, str]) -> dict:
    current_words = set(ctx["mapped"])
    added_words = {row["word"] for row in rows}
    after_words = current_words | added_words
    base = ctx["base"]
    pinyin = ctx["current_pinyin"]
    current_runtime_rows = []
    for filename in ctx["runtime_files"]:
        if filename in GENERATED_NAMES:
            continue
        path = DATA / filename
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            current_runtime_rows.append(line.split("\t"))
    reachable_before = {word for chinese, senses in base.items() if chinese in pinyin
                        for word, _pos in senses}
    reachable_before.update(row[1] for row in current_runtime_rows if row[0] in pinyin)
    overlay_chinese = {line.split("\t")[0] for line in overlay_payload.splitlines() if line}
    all_after_pinyin_keys = set(pinyin) | overlay_chinese
    reachable_after = {word for chinese, senses in base.items() if chinese in all_after_pinyin_keys
                       for word, _pos in senses}
    reachable_after.update(row[1] for row in current_runtime_rows if row[0] in all_after_pinyin_keys)
    reachable_after.update(row["word"] for row in rows
                           if row["chinese"] in all_after_pinyin_keys)
    coverage = ctx["coverage"]
    tags, ipa = ctx["tags"], ctx["ipa"]
    counts_by_source = collections.Counter(row["source"] for row in rows)
    count_by_target = {
        target: len({row["word"] for row in rows if tags[row["word"]] & (1 << BITS[target])})
        for target in TARGETS
    }
    input_files = [DUAL_PATH, COW_PATH, FMLD_PATH, KO_PATH, KO_MISSING_PATH,
                   OPEN_DICT_PATH, CEDICT_PATH, RIME_ROOT / "base.dict.yaml",
                   RIME_ROOT / "ext.dict.yaml"]
    inputs = {path.name: sha(path) for path in input_files}
    data_manifest = read_json(DATA / "manifest.json")
    inputs["pinned_english_tag_manifest_sha256"] = sha(DATA / "manifest.json")
    inputs["pinned_ecdict_sha256"] = next(row["sha256"] for row in data_manifest["input_files"]
                                            if row["path"] == "ecdict.csv")
    inputs["cc_cedict_sha256"] = "8172061b2a647dd8a179788830ef233944baee479bc7018f111064ad16d8f46f"
    inputs["fmld_sha256"] = "adffa622f223b33b03e76fd1d8f7c57cd90f6491cd5e9cec69a984ec1b3bc1ad"
    inputs["koreader_archive_sha256"] = "910d8fc3bf054f7a36f5db134f0624619711e5b414ebf7de45a3c0e04e98232c"
    inputs["open_dictionary_sha256"] = "69af69cdc685b5dce465613d1cc8fffb598eb46714f57cf73bd6606c2ceb7e43"
    inputs["rime_ice_commit"] = "da1fbe602e38f26db846fa10120ee64c2b0324c0"
    inputs["fmld_commit"] = "de1a3c543fb35ede7f46e335d12f28572578c2b6"
    inputs["cow_commit"] = "406bf83b3c507a3d1f26e88252d5d66893fd36bf"
    inputs["koreader_release"] = "v1.2.0"
    inputs["open_dictionary_release"] = "v2.0"
    inputs["openetymology_commit"] = "7d89f3697abf26e305fe2627f181b692c2c10b28"
    before, after = coverage(tags, current_words, ipa), coverage(tags, after_words, ipa)
    reachable_coverage_before = coverage(tags, reachable_before, ipa)
    reachable_coverage_after = coverage(tags, reachable_after, ipa)
    return {
        "batch": "11-exam-targets-conservative-multi-source-v1",
        "selected_pairs": len(rows), "selected_unique_headwords": len(added_words),
        "selected_new_pinyin_keys": len(overlay_chinese),
        "selected_by_source": dict(sorted(counts_by_source.items())),
        "added_headwords_by_target": count_by_target,
        "coverage_before": before, "coverage_after": after,
        "pinyin_reachable_coverage_before": reachable_coverage_before,
        "pinyin_reachable_coverage_after": reachable_coverage_after,
        "rejected_or_unselected": dict(sorted(rejected.items())),
        "selection": {
            "one_mapping_per_previously_unmapped_english_headword": True,
            "target_tags": ["tem4", "tem8", "toefl", "ielts"],
            "ipa_required": True,
            "pinyin": "Existing exact Qingjian key, exact CC-CEDICT pronunciation, or single-reading agreement from CC-CEDICT and Rime ICE; unresolved polyphonic readings are excluded.",
            "priority": "Source evidence first, then existing inputtable key, then current pinyin frequency; new keys have frequency 0 and append behind old candidates.",
            "max_extra_rows_per_chinese_key": 8,
            "chinese_candidate_order": "Existing dictionary rows are exported in their current order; appended rows have frequency 0, preserving all existing relative candidate order.",
            "review_limit": "Automated source cross-check and exact-gloss selection; this is not a claim of human review for every selected row.",
        },
        "inputs": inputs,
        "outputs": {
            "reviewed": {"sha256": hashlib.sha256(review_payload.encode()).hexdigest(), "rows": len(rows)},
            "pinyin_overlay": {"sha256": hashlib.sha256(overlay_payload.encode()).hexdigest(), "rows": len(overlay_chinese)},
            **{path.name: {"sha256": hashlib.sha256(payload.encode()).hexdigest(),
                           "rows": len(payload.splitlines())}
               for path, payload in expansion_payload_map.items()},
        },
        "licenses": {
            "ECDICT MIT": "separate file; see ECDICT-LICENSE",
            "KyleBing BSD-3-Clause": "separate file; see KyleBing-LICENSE",
            "Chinese Open Wordnet": "separate file with its upstream per-file notice and disclaimer",
            "CC BY-SA 4.0": "separate file; see source attribution documents for CC-CEDICT, FMLD, and KOReader dictionaries",
            "pinyin_overlay": "row-level source column; CC-CEDICT and Rime ICE terms remain attributed separately",
        },
        "limitations": "Coverage uses fixed community exam lists, not official complete syllabi. Mapping means an exact whole Chinese-to-English candidate mapping exists. Pinyin reachability means its full pinyin key exists; it does not promise the candidate is on page one.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--select", action="store_true", help="write the selected row-level evidence ledger")
    parser.add_argument("--check", action="store_true", help="verify deterministic candidate selection")
    args = parser.parse_args()
    fill_ecdict_pos()
    ctx = load_context()
    selected, rejected = load_candidates(ctx)
    review = make_review_payload(selected)
    pinyin_by_word: dict[str, tuple[str, str]] = {}
    current = ctx["current_pinyin"]
    for row in selected:
        if row["chinese"] in current:
            continue
        old = pinyin_by_word.get(row["chinese"])
        value = (row["pinyin"], row["pinyin_source"])
        if old and old[0] != value[0]:
            raise SystemExit(f"Selected mappings disagree on pinyin for {row['chinese']}")
        pinyin_by_word[row["chinese"]] = value
    overlay = "".join(f"{word}\t{pinyin}\t0\t{source}\n"
                      for word, (pinyin, source) in sorted(pinyin_by_word.items()))
    expansions = expansion_payloads(selected)
    manifest = make_manifest(selected, rejected, ctx, review, overlay, expansions)
    payloads = {REVIEWED: review, Pinyin_OUT: overlay, **expansions,
                MANIFEST_OUT: json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"}
    if args.check:
        changed = [str(path) for path, payload in payloads.items()
                   if not path.is_file() or path.read_text(encoding="utf-8") != payload]
        if changed:
            raise SystemExit("Selected batch differs: " + ", ".join(changed))
    elif args.select:
        for path, payload in payloads.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload, encoding="utf-8", newline="\n")
    print(json.dumps({"selected_pairs": len(selected), "selected_headwords": len({r['word'] for r in selected}),
                      "selected_by_source": dict(sorted(collections.Counter(r["source"] for r in selected).items())),
                      "new_pinyin_keys": len(pinyin_by_word), "rejected": dict(sorted(rejected.items())),
                      "reviewed_sha256": hashlib.sha256(review.encode()).hexdigest(),
                      "pinyin_overlay_sha256": hashlib.sha256(overlay.encode()).hexdigest()},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
