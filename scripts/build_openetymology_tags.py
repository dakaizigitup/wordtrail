"""Build a separately attributed TEM8/TOEFL membership index from OpenEtymology.

Only headwords and list membership are extracted from the pinned CC BY-SA 4.0
wordbooks. Definitions, examples, etymologies, and audio are not redistributed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "7d89f3697abf26e305fe2627f181b692c2c10b28"
SOURCE = "openetymology/OpenEtymology"
LICENSE = "CC BY-SA 4.0"
CACHE = ROOT / "build/source-audit/openetymology" / COMMIT
OUT = ROOT / "vocabulary/data"
WORD = re.compile(r"[a-z]+(?:[-'][a-z]+)*\Z")
FILES = {
    "TEM8/TEM8.txt": {
        "target": "tem8", "mask": 1 << 3, "count": 3984,
        "sha256": "0d70fd4779399ec222308eaea7d81c0343e6a8416f887445c5687abb08561d6f",
    },
    "TOEFL/TOEFL.txt": {
        "target": "toefl", "mask": 1 << 4, "count": 4510,
        "sha256": "5aafb5f70e5414e87264466ea1cf0d41528397fbcd1d3b0bea00bacf8985f587",
    },
}
LICENSE_RECORD = {
    "path": "DATA_LICENSE.md",
    "url": f"https://raw.githubusercontent.com/{SOURCE}/{COMMIT}/DATA_LICENSE.md",
    "sha256": "a92399cf4721a4a80b8c05f6028729bb e2c230e48cb3cdc0e28cef6084651069".replace(" ", ""),
}


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def read_source(relative: str, record: dict[str, object], download: bool) -> bytes:
    path = CACHE / relative
    if not path.is_file() and download:
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://raw.githubusercontent.com/{SOURCE}/{COMMIT}/{relative}"
        with urllib.request.urlopen(url, timeout=60) as response:
            path.write_bytes(response.read())
    if not path.is_file():
        raise SystemExit(f"Missing pinned source {path}; rerun with --download")
    payload = path.read_bytes()
    if sha(payload) != record["sha256"]:
        raise SystemExit(f"Pinned source checksum mismatch: {relative}")
    return payload


def build(download: bool) -> tuple[dict[str, bytes], dict[str, object]]:
    membership: dict[str, int] = {}
    source_records = []
    for relative, record in FILES.items():
        payload = read_source(relative, record, download)
        words = [line.strip().casefold() for line in payload.decode("utf-8-sig").splitlines() if line.strip()]
        if len(words) != record["count"] or len(set(words)) != len(words):
            raise SystemExit(f"Unexpected headword count or duplicate in {relative}")
        invalid = [word for word in words if not WORD.fullmatch(word)]
        if invalid:
            raise SystemExit(f"Invalid headwords in {relative}: {invalid[:5]}")
        for word in words:
            membership[word] = membership.get(word, 0) | int(record["mask"])
        source_records.append({
            "path": relative,
            "target": record["target"],
            "words": len(words),
            "bytes": len(payload),
            "sha256": sha(payload),
            "url": f"https://github.com/{SOURCE}/blob/{COMMIT}/{relative}",
        })

    license_payload = read_source(LICENSE_RECORD["path"], LICENSE_RECORD, download)
    license_text = license_payload.decode("utf-8-sig")
    if "CC BY-SA 4.0" not in license_text:
        raise SystemExit("Pinned OpenEtymology data license no longer states CC BY-SA 4.0")
    rows = "".join(f"{word}\t{mask}\n" for word, mask in sorted(membership.items()))
    manifest = {
        "source": SOURCE,
        "commit": COMMIT,
        "license": LICENSE,
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "source_data_license_url": f"https://github.com/{SOURCE}/blob/{COMMIT}/DATA_LICENSE.md",
        "source_data_license_sha256": sha(license_payload),
        "wordbooks": source_records,
        "targets": {
            target: sum(bool(mask & bit) for mask in membership.values())
            for target, bit in (("tem8", 1 << 3), ("toefl", 1 << 4))
        },
        "unique_headwords": len(membership),
        "output": {
            "path": "openetymology-exam-tags.tsv",
            "format": "lowercase headword<TAB>six-category bitmask; only TEM8 and TOEFL bits are set",
            "rows": len(membership),
            "bytes": len(rows.encode("utf-8")),
            "sha256": sha(rows.encode("utf-8")),
        },
        "scope": "Headwords and target-list membership only; no source definitions, examples, etymology, or audio. This community wordlist is not an official complete syllabus.",
    }
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    return {
        OUT / "openetymology-exam-tags.tsv": rows.encode("utf-8"),
        OUT / "openetymology-tags-manifest.json": manifest_text.encode("utf-8"),
        OUT / "OPENETYMOLOGY-DATA-ATTRIBUTION.md": (
            "# OpenEtymology exam-wordlist attribution\n\n"
            f"Source: [{SOURCE}](https://github.com/{SOURCE}/tree/{COMMIT}), fixed commit `{COMMIT}`.\n\n"
            "The public TEM8 and TOEFL text wordbooks declare CC BY-SA 4.0 in `DATA_LICENSE.md`. "
            "This project extracts normalized lowercase headwords and list membership only. It does not redistribute "
            "the wordbook definitions, examples, etymologies, or audio. The generated headword-membership file and "
            "its adaptations are provided under CC BY-SA 4.0.\n\n"
            f"Data license: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). "
            f"Data-license statement: https://github.com/{SOURCE}/blob/{COMMIT}/DATA_LICENSE.md\n\n"
            "Pinned source files and SHA-256 values are recorded in `openetymology-tags-manifest.json`. "
            "This is a community wordlist, not an official complete exam syllabus.\n"
        ).encode("utf-8"),
        OUT / "OPENETYMOLOGY-DATA-LICENSE.txt": license_payload,
    }, manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="download missing pinned upstream files")
    parser.add_argument("--check", action="store_true", help="verify generated files without writing")
    args = parser.parse_args()
    expected, manifest = build(args.download)
    if args.check:
        changed = [str(path) for path, payload in expected.items() if not path.is_file() or path.read_bytes() != payload]
        if changed:
            raise SystemExit("OpenEtymology generated files differ: " + ", ".join(changed))
    else:
        for path, payload in expected.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
