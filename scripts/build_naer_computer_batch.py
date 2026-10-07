"""Build a reviewed computer-terms tranche from pinned NAER open data."""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
SOURCE_CSV = DATA / "sources/naer/computer-academic-terms-2026-08-12.csv"
SOURCE_METADATA = DATA / "sources/naer/computer-dataset.json"
SOURCE_SHA256 = "d8d65ba4097d45dd1c5d6b737fc942a1bd92d74d76ce6d6fb5348001b11b75bd"
SOURCE_METADATA_SHA256 = "dd25996dca84a0e357228d8bb2d96bcd88609f87dfc0ee2763cf96eb85ab679e"
PREFILTER = DATA / "batches/31-naer-computer-prefilter.tsv"
CANDIDATES = DATA / "batches/31-naer-computer-candidates.tsv"
REVIEWED = DATA / "batches/31-naer-computer-reviewed.tsv"
TAG_REVIEWED = DATA / "batches/31-naer-computer-tags-reviewed.tsv"
EXPANSION = DATA / "naer-computer-expansion.tsv"
TAGS = DATA / "naer-computer-tags.tsv"
MANIFEST = DATA / "naer-computer-manifest.json"

SOURCE = "NAER Computer Science Academic Terms OGDL v1.0"
COMPUTER_BIT = 1 << 6
WORD = re.compile(r"[a-z][a-z'-]*\Z")
EN_SEPARATORS = re.compile(r"[;；]+")
POS_MARKERS = re.compile(r"【[^】]*】")
OPTIONAL = re.compile(r"\[([^\[\]]+)\]")
PARENTHETICAL = re.compile(r"（[^（）]*）|\([^()]*\)")
HAN = re.compile(r"[\u3400-\u9fff]+")

PREFILTER_FIELDS = (
    "chinese", "english", "ecdict_pos", "source_records", "source_fields",
    "source_traditional", "source_mainland", "pinyin", "pinyin_frequency",
    "ipa_sources", "already_mapped", "existing_headword", "already_computer_tag",
    "spare_capacity",
)
REVIEW_FIELDS = PREFILTER_FIELDS + ("decision", "runtime_pos", "review_note")
TAG_FIELDS = (
    "english", "source_records", "source_pairs", "already_computer_tag",
    "decision", "review_note",
)

# Each accepted mapping is selected from an exact local ECDICT gloss and the
# official glossary, then checked for useful computing-context fit.
ACCEPTED: dict[tuple[str, str], tuple[str, str]] = {
    ("中断", "break"): ("n.", "The NAER computer glossary lists 中断 for break; this is a standard interruption or communication-break sense."),
    ("中止", "suspend"): ("v.", "The glossary lists 中止 for suspend; suspending a process or operation is a standard computing action."),
    ("亮度", "luminosity"): ("n.", "亮度 is the exact local noun gloss and a useful display/graphics property."),
    ("优先", "priority"): ("n.", "Priority is a standard scheduling and computing concept; 优先 is an exact local gloss."),
    ("传染", "infection"): ("n.", "The glossary's information-security context and the exact local gloss support computer-virus infection."),
    ("修正", "modification"): ("n.", "The source lists 修改/修正; this is a useful software or data modification sense."),
    ("变形", "morphing"): ("n.", "Morphing is a computer-graphics transformation; 变形 is the exact source and local gloss."),
    ("否定", "negation"): ("n.", "Negation is a formal logic and programming concept; 否定 is exact."),
    ("响应", "response"): ("n.", "Response is a standard system, client/server, and interface term; 响应 is exact."),
    ("图形", "graph"): ("n.", "The source lists 图形/图 for graph; this is a valid graph-theory and computing sense."),
    ("基数", "radix"): ("n.", "Radix is the base of a numeral system; 基数 is the exact technical translation."),
    ("复制", "replication"): ("n.", "Replication is a standard data/database operation; 复制 is exact."),
    ("威胁", "threat"): ("n.", "Threat is a core information-security term; 威胁 is exact."),
    ("定义", "definition"): ("n.", "Definition is a standard programming and data-model term; 定义 is exact."),
    ("干线", "trunk"): ("n.", "Trunk is a networking/telecommunications term; 干线 is the exact source gloss."),
    ("引用", "reference"): ("v.", "The source distinguishes 引用 as a verb; referencing is a standard programming action."),
    ("指示器", "indicator"): ("n.", "Indicator is a useful interface and system-status term; 指示器 is exact."),
    ("提交", "submission"): ("n.", "Submission is used for forms and system requests; 提交 is the exact local gloss."),
    ("操作", "operation"): ("n.", "Operation is a standard computing/system concept; 操作 is exact."),
    ("攻破", "breach"): ("v.", "Breach as a verb is used for breaking a system's security; 攻破 is the source and local gloss."),
    ("文件", "document"): ("n.", "The official computer glossary and local dictionary agree on 文件 for a document."),
    ("服务", "service"): ("n.", "Service is a standard software/networking concept; 服务 is exact."),
    ("检索", "retrieval"): ("n.", "Retrieval is a standard information-retrieval concept; 检索 is exact."),
    ("正文", "text"): ("n.", "The source lists 正文/本文 for text; this is a useful document-processing sense."),
    ("泄露", "disclosure"): ("n.", "Disclosure is a common information-security concept; 泄露 is exact."),
    ("清除", "purge"): ("n.", "Purge is used for clearing stored or obsolete data; 清除 is an exact local noun gloss."),
    ("移位", "shift"): ("n.", "移位 is the standard bit-shift/position-shift sense in computing."),
    ("等价", "equivalence"): ("n.", "Equivalence is a formal logic and computing concept; 等价 is exact."),
    ("约束", "constraint"): ("n.", "Constraint is a standard programming, database, and optimization term; 约束 is exact."),
    ("组件", "module"): ("n.", "The source lists 组件 for module; this is a standard software-component sense."),
    ("缓冲区", "buffer"): ("n.", "Buffer is a core computing concept; 缓冲区 is the exact technical translation."),
    ("覆盖", "overlay"): ("n.", "Overlay is used in graphics and system interfaces; 覆盖 is the exact source and local gloss."),
    ("解析", "resolve"): ("v.", "The source specifies address resolution; 解析 is the exact local verb gloss."),
    ("记号", "notation"): ("n.", "Notation is used in programming and formal systems; 记号 is exact."),
    ("语法", "syntax"): ("n.", "Syntax is a core programming-language term; 语法 is exact."),
    ("运算", "operation"): ("n.", "Operation as 运算 is a useful arithmetic and computing sense, distinct from 操作."),
    ("连接", "connection"): ("n.", "Connection is a standard networking concept; 连接 is exact."),
    ("闪烁", "blink"): ("n.", "Blink is used for cursor, indicator, and display behavior; 闪烁 is exact."),
    ("陈述", "statement"): ("n.", "Statement is a standard programming-language construct; 陈述 is exact."),
    ("顺序", "sequence"): ("n.", "Sequence is a standard data and control-flow concept; 顺序 is the exact source/local gloss."),
}

REJECTED: dict[tuple[str, str], str] = {
    ("允许", "permission"): "允许 reads as an action; the usual standalone noun translation is 权限/许可, so this exact source variant is not added.",
    ("取消", "undo"): "取消 means cancel; the usual UI action for undo is 撤销, so this source variant could mislead.",
    ("哄骗", "spoofing"): "哄骗 is too broad and does not express the technical impersonation/forgery sense precisely.",
    ("地点", "site"): "地点 means a place; it is not an appropriate translation of a website/site in this context.",
    ("目的", "destination"): "目的 is not the exact computing destination term; the source's other candidate meanings require context.",
    ("移动", "shift"): "The source gives a distinct 移位 sense for computing; the broad 移动 mapping is not added.",
    ("蓄电池", "accumulator"): "The source also lists 累加器, but the exact local noun gloss available here is 蓄电池, which is not the computing sense.",
    ("轰炸", "bombing"): "The isolated meaning is not a useful computer term without a specific attack phrase.",
}

# These are existing mappings whose English headwords are unambiguously useful
# in the computer target. New accepted mappings are tagged automatically.
TAG_ACCEPTED: dict[str, str] = {
    "allocation": "Allocation is a standard memory/resource-management concept, and the official glossary provides an exact local translation; the Chinese key is already at capacity so only the category tag is added.",
    "mainframe": "The NAER source identifies mainframe as 大型电脑/主机.",
    "blog": "The source gives blog as 博客/网志, an internet publishing term.",
    "variable": "Variable is a standard programming and data concept; the source gives 变量.",
    "spam": "The source identifies spam as 垃圾邮件, an email/network term.",
    "multimedia": "The source gives 多媒体, an unambiguous computing/media term.",
    "workstation": "Workstation is a computing device/category; the source gives 工作站.",
    "application": "The source explicitly gives 应用(软件)/应用(系统).",
    "switch": "The source includes 交换器, a network-device sense of switch.",
    "loop": "Loop is a standard programming/control-flow concept; the source gives 循环.",
    "speaker": "The source identifies speaker as 扬声器/喇叭, a computer peripheral.",
    "index": "The source includes 索引, a standard database/search structure.",
    "integer": "Integer is a standard data type; the source gives 整数.",
    "format": "Format is a standard file/data representation term; the source gives 格式.",
    "file": "The source gives 档案 for file, a core computer term.",
    "computer": "The official source directly identifies 电脑/计算机.",
    "monitor": "The source includes 显示器 and 监视器, a computer display/system process sense.",
    "collision": "Collision is a standard networking term; the source includes 碰撞.",
    "process": "The source distinguishes 程序/过程 for process; this is a core computing term.",
    "infrared": "The source includes infrared, used in computer communications and devices.",
    "hertz": "Hertz is a standard computing hardware frequency unit; the source gives 赫兹.",
    "input": "Input is a core computing and interface term; the source gives 输入.",
    "output": "Output is a core computing and interface term; the source gives 输出.",
    "selection": "The source includes selection structure, a programming control-flow concept.",
    "privacy": "Privacy is a standard information-security and data-protection term.",
    "microphone": "The source identifies microphone as 麦克风/话筒, a computer peripheral.",
    "pixel": "Pixel is a core graphics/display term.",
    "kernel": "Kernel is a core operating-system term.",
    "character": "Character is a standard text-encoding and computing term.",
    "constant": "Constant is a standard programming concept.",
    "stack": "Stack is a standard data structure and runtime concept.",
    "buffer": "Buffer is a core computing term.",
    "core": "Core is a standard processor/system term.",
    "keyboard": "Keyboard is a computer peripheral.",
    "desktop": "Desktop is a computer form factor and user-interface term.",
    "proxy": "Proxy is a standard networking concept.",
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
        raise SystemExit("Pinned NAER computer glossary CSV SHA-256 mismatch")
    metadata_bytes = SOURCE_METADATA.read_bytes()
    if SOURCE_METADATA_SHA256 and sha(metadata_bytes) != SOURCE_METADATA_SHA256:
        raise SystemExit("Pinned NAER computer glossary metadata SHA-256 mismatch")
    metadata = json.loads(metadata_bytes.decode("utf-8-sig"))
    if metadata.get("dataset_id") != "15275" or metadata.get("snapshot_sha256") != SOURCE_SHA256:
        raise SystemExit("Unexpected NAER computer glossary metadata")

    sys.path.insert(0, str(ROOT / "scripts"))
    import build_finance_i18n_batch as finance_batch

    inputs = finance_batch.load_inputs()
    runtime_source = (ROOT / "vocabulary/src/expansion/mod.rs").read_text(encoding="utf-8")
    compiled = set(re.findall(r'include_str!\("../../data/([^" ]+\.tsv)"\)', runtime_source))
    runtime_files = sorted(compiled - {EXPANSION.name})
    for filename in runtime_files:
        for line in (DATA / filename).read_text(encoding="utf-8").splitlines():
            fields = line.split("\t")
            if len(fields) < 3:
                continue
            chinese, english = fields[0], fields[1].casefold()
            pair = (chinese, english)
            if pair not in inputs["pairs"]:
                inputs["pairs"].add(pair)
                inputs["extras"][chinese] = inputs["extras"].get(chinese, 0) + 1
            inputs["words"].add(english)
    inputs["runtime_files"] = runtime_files
    inputs["runtime_hashes"] = {name: sha((DATA / name).read_bytes()) for name in runtime_files}
    existing_computer_tags = set()
    for filename in ("professional-domain-tags.tsv", "cjk-compsci-tags.tsv", "computerese-tags.tsv"):
        for line in (DATA / filename).read_text(encoding="utf-8").splitlines():
            fields = line.split("\t")
            if len(fields) >= 2 and int(fields[1]) & COMPUTER_BIT:
                existing_computer_tags.add(fields[0].casefold())
    inputs["existing_computer_tags"] = existing_computer_tags
    return inputs


def optional_forms(value: str) -> list[str]:
    matches = list(OPTIONAL.finditer(value))
    if len(matches) > 8:
        return [OPTIONAL.sub(lambda m: m.group(1), value)]
    forms = []
    for include in itertools.product((False, True), repeat=len(matches)):
        cursor, pieces = 0, []
        for match, keep in zip(matches, include):
            pieces.append(value[cursor:match.start()])
            if keep:
                pieces.append(match.group(1))
            cursor = match.end()
        pieces.append(value[cursor:])
        forms.append("".join(pieces))
    return forms or [value]


def chinese_variants(value: str, converter) -> set[str]:
    value = POS_MARKERS.sub("", value.strip())
    value = PARENTHETICAL.sub(" ", value)
    terms = set()
    for form in optional_forms(value):
        for term in HAN.findall(form):
            simplified = converter.convert(term).strip()
            if simplified:
                terms.add(simplified)
    return terms


def discover(inputs: dict) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    sys.path.insert(0, str(ROOT / "build/vocab-tools"))
    from opencc import OpenCC

    converter = OpenCC("t2s")
    grouped: dict[tuple[str, str], dict] = {}
    ipa = inputs["uk"] | inputs["us"]
    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        expected = ("序號", "英文名稱", "中文名稱", "中國大陸譯名", "來源網站")
        if tuple(reader.fieldnames or ()) != expected:
            raise SystemExit(f"Unexpected NAER computer CSV columns: {reader.fieldnames}")
        for source in reader:
            for raw_english in EN_SEPARATORS.split(source["英文名稱"].strip()):
                english = raw_english.strip().strip("()").casefold()
                if not WORD.fullmatch(english) or english not in ipa:
                    continue
                exact_pos: dict[str, set[str]] = defaultdict(set)
                for gloss, pos in inputs["ecdict"].get(english, set()):
                    exact_pos[gloss].add(pos)
                if not exact_pos:
                    continue
                for field, raw_value in (("traditional", source["中文名稱"]), ("mainland", source["中國大陸譯名"])):
                    for chinese in chinese_variants(raw_value, converter):
                        if chinese not in inputs["pinyin"] or chinese not in exact_pos:
                            continue
                        item = grouped.setdefault((chinese, english), {
                            "positions": set(), "rows": set(), "fields": set(),
                            "traditional": set(), "mainland": set(),
                        })
                        item["positions"].update(exact_pos[chinese])
                        item["rows"].add(source["序號"].strip())
                        item["fields"].add(field)
                        if source["中文名稱"].strip():
                            item["traditional"].add(source["中文名稱"].strip())
                        if source["中國大陸譯名"].strip():
                            item["mainland"].add(source["中國大陸譯名"].strip())

    rows = []
    for (chinese, english), item in sorted(grouped.items()):
        pinyin, frequency = inputs["pinyin"][chinese]
        rows.append({
            "chinese": chinese,
            "english": english,
            "ecdict_pos": ",".join(sorted(item["positions"])),
            "source_records": ",".join(sorted(item["rows"], key=int)),
            "source_fields": ",".join(sorted(item["fields"])),
            "source_traditional": " | ".join(sorted(item["traditional"])),
            "source_mainland": " | ".join(sorted(item["mainland"])),
            "pinyin": pinyin,
            "pinyin_frequency": str(frequency),
            "ipa_sources": ",".join(name for name, words in (("UK", inputs["uk"]), ("US", inputs["us"])) if english in words),
            "already_mapped": str((chinese, english) in inputs["pairs"]).lower(),
            "existing_headword": str(english in inputs["words"]).lower(),
            "already_computer_tag": str(english in inputs["existing_computer_tags"]).lower(),
            "spare_capacity": str(inputs["extras"].get(chinese, 0) < 8).lower(),
        })
    candidates = [row for row in rows if row["already_mapped"] == "false" and row["spare_capacity"] == "true"]
    return rows, candidates


def review(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    reviewed = []
    found = set()
    for row in candidates:
        key = (row["chinese"], row["english"])
        if key in ACCEPTED:
            pos, note = ACCEPTED[key]
            if pos not in row["ecdict_pos"].split(","):
                raise SystemExit(f"Curated POS is absent for {key}: {pos} vs {row['ecdict_pos']}")
            decision = "accept"
            found.add(key)
        elif key in REJECTED:
            pos, note, decision = row["ecdict_pos"].split(",")[0], REJECTED[key], "reject"
        else:
            pos, decision = row["ecdict_pos"].split(",")[0], "defer"
            note = "Exact source term, ECDICT gloss, pinyin, and IPA passed; computing-specific usefulness or the standalone Chinese sense needs stronger context, so it is kept out pending review."
        reviewed.append({**row, "decision": decision, "runtime_pos": pos, "review_note": note})
    missing = set(ACCEPTED) - found
    if missing:
        raise SystemExit(f"Curated accepted computer mappings absent from candidates: {sorted(missing)}")
    return reviewed


def build(prefilter: list[dict[str, str]], candidates: list[dict[str, str]], reviewed: list[dict[str, str]], inputs: dict) -> dict[Path, bytes]:
    accepted = [row for row in reviewed if row["decision"] == "accept"]
    rejected = [row for row in reviewed if row["decision"] == "reject"]
    deferred = [row for row in reviewed if row["decision"] == "defer"]
    if len({(row["chinese"], row["english"]) for row in accepted}) != len(accepted):
        raise SystemExit("Duplicate accepted NAER computer mappings")

    per_key: dict[str, int] = defaultdict(int)
    expansion_rows = []
    for row in accepted:
        chinese, english = row["chinese"], row["english"]
        if (chinese, english) in inputs["pairs"] or chinese not in inputs["pinyin"]:
            raise SystemExit(f"Accepted NAER computer mapping already exists or is unreachable: {chinese} -> {english}")
        if inputs["extras"].get(chinese, 0) + per_key[chinese] >= 8:
            raise SystemExit(f"Accepted NAER computer mapping exceeds per-key limit: {chinese} -> {english}")
        per_key[chinese] += 1
        expansion_rows.append({"chinese": chinese, "english": english, "pos": row["runtime_pos"], "source": SOURCE})

    exact_pairs = {(row["chinese"], row["english"]) for row in prefilter}
    tag_decisions = {}
    tag_deferred = {}
    for word, note in TAG_ACCEPTED.items():
        if not any(english == word for _, english in exact_pairs):
            tag_deferred[word] = "The pinned source did not yield an exact local ECDICT gloss + pinyin + IPA pair for this headword, so its computer tag is not added from this batch."
        else:
            tag_decisions[word] = note
    for row in accepted:
        tag_decisions.setdefault(row["english"], "The accepted mapping is an exact term in the NAER computer-science glossary.")
    tag_rows = [
        {"english": word, "mask": str(COMPUTER_BIT), "source": SOURCE}
        for word in sorted(tag_decisions)
    ]
    expansion_rows.sort(key=lambda row: (row["chinese"], row["english"], row["pos"]))
    tag_review_rows = []
    for word, note in sorted(tag_decisions.items()):
        matching = [row for row in prefilter if row["english"] == word]
        tag_review_rows.append({
            "english": word,
            "source_records": ",".join(sorted({n for row in matching for n in row["source_records"].split(",")}, key=int)),
            "source_pairs": " | ".join(f"{row['chinese']} -> {word}" for row in matching),
            "already_computer_tag": str(word in inputs["existing_computer_tags"]).lower(),
            "decision": "accept",
            "review_note": note,
        })
    for word, note in sorted(tag_deferred.items()):
        tag_review_rows.append({
            "english": word,
            "source_records": "",
            "source_pairs": "",
            "already_computer_tag": str(word in inputs["existing_computer_tags"]).lower(),
            "decision": "defer",
            "review_note": note,
        })
    tag_review_rows.sort(key=lambda row: row["english"])

    prefilter_bytes = write_tsv(PREFILTER, PREFILTER_FIELDS, prefilter)
    candidate_bytes = write_tsv(CANDIDATES, PREFILTER_FIELDS, candidates)
    reviewed_bytes = write_tsv(REVIEWED, REVIEW_FIELDS, reviewed)
    tag_review_bytes = write_tsv(TAG_REVIEWED, TAG_FIELDS, tag_review_rows)
    expansion_bytes = write_tsv(EXPANSION, ("chinese", "english", "pos", "source"), expansion_rows, header=False)
    tags_bytes = write_tsv(TAGS, ("english", "mask", "source"), tag_rows, header=False)
    source_hashes = {
        SOURCE_CSV.name: SOURCE_SHA256,
        SOURCE_METADATA.name: sha(SOURCE_METADATA.read_bytes()),
        **inputs["runtime_hashes"],
    }
    with SOURCE_CSV.open(encoding="utf-8-sig", newline="") as stream:
        source_count = sum(1 for _ in csv.DictReader(stream))
    new_headwords = sorted({row["english"] for row in accepted if row["existing_headword"] == "false"})
    manifest = {
        "batch": "31-naer-computer-science-terms",
        "source": {
            "title": "National Academy for Educational Research - Cross-Strait Comparative Terminology - Computer Science",
            "provider": "National Academy for Educational Research",
            "dataset_id": "15275",
            "dataset_url": "https://data.gov.tw/dataset/15275",
            "resource_url": "https://opendata.naer.edu.tw/學術名詞/國家教育研究院-兩岸對照名詞-計算機學術名詞.csv",
            "license": "Open Government Data License v1.0",
            "license_url": "https://data.gov.tw/license",
            "portal_updated_at": "2026-08-12 15:06",
            "snapshot_sha256": SOURCE_SHA256,
            "snapshot_bytes": SOURCE_CSV.stat().st_size,
            "records": source_count,
        },
        "filters": "Single-word English entries with local UK/US IPA, exact ECDICT Chinese gloss and part of speech, and an existing pinyin key. Both the source Traditional Chinese and Mainland translation column are screened; no source definitions are copied.",
        "runtime_inputs_sha256": inputs["hashes"],
        "runtime_expansion_inputs": inputs["runtime_files"],
        "runtime_expansion_sha256": inputs["runtime_hashes"],
        "candidate_exact_pairs": len(prefilter),
        "already_mapped_pairs": sum(row["already_mapped"] == "true" for row in prefilter),
        "new_mapping_candidates_with_capacity": len(candidates),
        "accepted_new_mappings": len(accepted),
        "rejected_new_mappings": len(rejected),
        "deferred_new_mappings": len(deferred),
        "accepted_new_headwords": len(new_headwords),
        "new_headwords": new_headwords,
        "computer_tag_source_memberships": len(tag_rows),
        "new_unique_computer_tag_headwords": [row["english"] for row in tag_rows if row["english"] not in inputs["existing_computer_tags"]],
        "computer_tag_candidates_deferred_without_exact_local_pair": sorted(tag_deferred),
        "mapping_rows": [f"{row['chinese']} -> {row['english']} ({row['pos']})" for row in expansion_rows],
        "outputs": {
            PREFILTER.relative_to(DATA).as_posix(): {"rows": len(prefilter), "sha256": sha(prefilter_bytes)},
            CANDIDATES.relative_to(DATA).as_posix(): {"rows": len(candidates), "sha256": sha(candidate_bytes)},
            REVIEWED.relative_to(DATA).as_posix(): {"rows": len(reviewed), "sha256": sha(reviewed_bytes)},
            TAG_REVIEWED.relative_to(DATA).as_posix(): {"rows": len(tag_review_rows), "sha256": sha(tag_review_bytes)},
            EXPANSION.name: {"rows": len(expansion_rows), "sha256": sha(expansion_bytes)},
            TAGS.name: {"rows": len(tag_rows), "sha256": sha(tags_bytes)},
        },
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return {PREFILTER: prefilter_bytes, CANDIDATES: candidate_bytes, REVIEWED: reviewed_bytes,
            TAG_REVIEWED: tag_review_bytes, EXPANSION: expansion_bytes, TAGS: tags_bytes}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--discover", action="store_true")
    args = parser.parse_args()
    inputs = load_inputs()
    prefilter, candidates = discover(inputs)
    if args.discover:
        print(json.dumps({
            "exact_source_ecdict_pinyin_ipa_pairs": len(prefilter),
            "already_mapped_pairs": sum(row["already_mapped"] == "true" for row in prefilter),
            "new_mapping_candidates_with_capacity": len(candidates),
            "new_headword_candidates": len({row["english"] for row in candidates if row["existing_headword"] == "false"}),
            "accepted_mapping_decisions_present": sum((row["chinese"], row["english"]) in ACCEPTED for row in candidates),
        }, ensure_ascii=False, indent=2))
        return
    for path, content in build(prefilter, candidates, review(candidates), inputs).items():
        path.write_bytes(content)
        print(f"{path.relative_to(ROOT)}: {len(content)} bytes")


if __name__ == "__main__":
    main()
