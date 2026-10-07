"""Build a derived QJ dictionary while keeping the pinned official input intact."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"
OVERLAYS = (
    (DATA / "pinyin-overlays/exam-target-batch-11.tsv",
     "a42e86df9afbf2a6a811cb2e844545c8e1b4b6df40fcf81f1dd333ef0be7d859"),
    (DATA / "pinyin-overlays/exam-target-batch-12.tsv",
     "60c6e0648bfe16e18566088db22ef51fde8437c42ce314843774f6691e13b1d9"),
    (DATA / "pinyin-overlays/exam-target-batch-13.tsv",
     "2bff3ae926be131d4edc0f1871dfecc566889d24e0d4d62838972372a3a94fb5"),
)
SOURCE_DICT = ROOT / "data/dict.qj"
RUNTIME = ROOT / "build/runtime-data"
RUNTIME_TSV = RUNTIME / "dict.tsv"
RUNTIME_DICT = RUNTIME / "dict.qj"
BASE_TSV = ROOT / "build/runtime-data/base-dict.tsv"
BASE_SHA256 = "3e33b16a84df555e6f16d52ac8ab3c2c6b6f1f71734e69463861fd5abd9c19dc"
EXPORTER = ROOT / "target/debug/export_dictionary_tsv.exe"
EXTERNAL_CARGO_CWD = Path(f"{ROOT.drive}\\")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: list[str], cwd: Path = ROOT) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def export_base() -> None:
    if sha(SOURCE_DICT) != BASE_SHA256:
        raise SystemExit("Pinned official dictionary input changed")
    RUNTIME.mkdir(parents=True, exist_ok=True)
    if EXPORTER.is_file():
        run([str(EXPORTER), str(SOURCE_DICT), str(BASE_TSV)])
    else:
        run(["cargo", "run", "--locked", "--quiet", "-p", "wordtrail-mobile",
             "--bin", "export_dictionary_tsv", "--", str(SOURCE_DICT), str(BASE_TSV)])


def read_rows(path: Path) -> list[tuple[str, str, int]]:
    rows = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        fields = raw.split("\t")
        if len(fields) < 3:
            raise ValueError(f"Invalid dictionary TSV at {path}:{line_number}")
        word, pinyin, frequency = fields[:3]
        if not word or not pinyin or not pinyin.isascii() or not pinyin.replace(" ", "").isalpha():
            raise ValueError(f"Invalid word or pinyin at {path}:{line_number}")
        rows.append((word, pinyin, int(frequency)))
    return rows


def build_tsv() -> dict:
    original = read_rows(BASE_TSV)
    overlay_rows = []
    original_surfaces = {word for word, _, _ in original}
    overlay_surfaces: set[str] = set()
    overlay_hashes = {}
    for overlay, expected_sha in OVERLAYS:
        if not overlay.is_file():
            raise SystemExit(f"Missing pinyin overlay: {overlay}")
        overlay_sha = sha(overlay)
        if overlay_sha != expected_sha:
            raise SystemExit(f"Pinned pinyin overlay checksum mismatch: {overlay.name}")
        overlay_hashes[overlay.name] = overlay_sha
        for line_number, raw in enumerate(overlay.read_text(encoding="utf-8").splitlines(), 1):
            fields = raw.split("\t")
            if len(fields) != 4:
                raise ValueError(f"Invalid overlay row at {overlay}:{line_number}")
            word, pinyin, frequency, source = fields
            if not word or not pinyin or not pinyin.isascii() or not pinyin.replace(" ", "").isalpha():
                raise ValueError(f"Invalid overlay word or pinyin at {overlay}:{line_number}")
            if word in original_surfaces:
                raise ValueError(f"Overlay changes an existing Chinese candidate: {word}")
            if word in overlay_surfaces:
                raise ValueError(f"Overlays duplicate a new Chinese candidate: {word}")
            if int(frequency) != 0:
                raise ValueError(f"Overlay frequency must be zero to keep existing candidates ahead: {word}")
            if not source:
                raise ValueError(f"Overlay source is required: {word}")
            overlay_surfaces.add(word)
            overlay_rows.append((word, pinyin, 0))

    # The upstream parser uses a stable sort. Original rows are emitted first;
    # new rows have frequency zero, so they append after every existing match.
    merged = original + overlay_rows
    RUNTIME_TSV.write_text("".join(f"{word}\t{pinyin}\t{frequency}\n" for word, pinyin, frequency in merged),
                           encoding="utf-8", newline="\n")
    return {
        "input_sha256": BASE_SHA256,
        "overlays": overlay_hashes,
        "base_entries": len(original),
        "overlay_entries": len(overlay_rows),
        "runtime_entries": len(merged),
        "runtime_tsv_sha256": sha(RUNTIME_TSV),
    }


def pack() -> None:
    RUNTIME_DICT.unlink(missing_ok=True)
    run(["cargo", "run", "--locked", "--quiet", "--manifest-path",
         str(ROOT / "vendor/qingjian/Cargo.toml"), "-p", "qingjian-dict-convert", "--",
         "--out-dir", str(RUNTIME), "pack", "dict", "--input", str(RUNTIME_TSV),
         "--name", "词伴考试词汇拼音词库", "--license", "Mixed; see NOTICE.txt",
         "--attribution", "Qingjian v0.1.4 pinned base; Wordtrail exam vocabulary overlay; see NOTICE.txt",
         "--source", "https://github.com/dakaizigitup/wordtrail",
         "--data-version", "Wordtrail 0.1.27"], cwd=EXTERNAL_CARGO_CWD)


def verify_order() -> dict:
    merged_tsv = RUNTIME / "verified-runtime-dict.tsv"
    if EXPORTER.is_file():
        run([str(EXPORTER), str(RUNTIME_DICT), str(merged_tsv)])
    else:
        run(["cargo", "run", "--locked", "--quiet", "-p", "wordtrail-mobile",
             "--bin", "export_dictionary_tsv", "--", str(RUNTIME_DICT), str(merged_tsv)])
    before = read_rows(BASE_TSV)
    after = read_rows(merged_tsv)
    by_key_before: dict[str, list[tuple[str, int]]] = defaultdict(list)
    by_key_after: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for word, key, freq in before:
        by_key_before[key].append((word, freq))
    for word, key, freq in after:
        by_key_after[key].append((word, freq))
    for key, rows in by_key_before.items():
        old_surfaces = {word for word, _ in rows}
        retained = [(word, freq) for word, freq in by_key_after[key] if word in old_surfaces]
        if retained != rows:
            raise SystemExit(f"Existing candidate order changed for pinyin key {key}")
        for word, freq in by_key_after[key]:
            if word not in old_surfaces and freq > min((n for _, n in rows), default=1):
                raise SystemExit(f"Overlay entry promoted ahead of existing candidates for {key}")
    merged_tsv.unlink(missing_ok=True)
    return {"existing_order_preserved": True, "checked_pinyin_keys": len(by_key_before),
            "checked_existing_entries": len(before), "runtime_dictionary_sha256": sha(RUNTIME_DICT),
            "runtime_dictionary_bytes": RUNTIME_DICT.stat().st_size}


def prepare(export: bool, do_pack: bool) -> dict:
    if export or not BASE_TSV.is_file():
        export_base()
    stats = build_tsv()
    old_manifest = {}
    if (RUNTIME / "manifest.json").is_file():
        try:
            old_manifest = json.loads((RUNTIME / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            old_manifest = {}
    if do_pack or not RUNTIME_DICT.is_file() or old_manifest.get("runtime_tsv_sha256") != stats["runtime_tsv_sha256"]:
        pack()
    stats.update(verify_order())
    (RUNTIME / "manifest.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-base", action="store_true", help="re-export every original dictionary row")
    parser.add_argument("--repack", action="store_true", help="rebuild the QJ container")
    args = parser.parse_args()
    prepare(args.refresh_base, args.repack)


if __name__ == "__main__":
    main()
