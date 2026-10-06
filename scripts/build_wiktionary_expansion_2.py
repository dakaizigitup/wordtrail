"""Build the second, source-pinned Wiktionary vocabulary tranche."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_wiktionary_expansion import DATA, build_payloads


ROOT = Path(__file__).resolve().parents[1]
CURATION = DATA / "batches/06-wiktionary-zh-reviewed.tsv"
OUTPUT = DATA / "wiktionary-expansion-2.tsv"
MANIFEST = DATA / "wiktionary-manifest-2.json"
PRIOR = (
    DATA / "wiktionary-expansion.tsv",
    DATA / "cccedict-expansion.tsv",
    DATA / "cccedict-expansion-2.tsv",
)
DISCOVERY_SNAPSHOT = {
    "project": "buchwandler/lexhint-datasets",
    "artifact": "lexhint-zh-english-dictionary-s10-2026.09.09.sqlite3.gz",
    "artifact_url": "https://github.com/buchwandler/lexhint-datasets/releases",
    "artifact_sha256": "1bc71e741f884c3ef9ac801397b3dabfbf39ecd3ba666ca08d8a4206eaf114ac",
    "uncompressed_artifact_sha256": "98fef9ba82047d0eaba650c1da074810c135da3c90e1fdb59f2faf197d6b7dd2",
    "wiktionary_language_split_sha256": "adc32196f47344c894a83fb2d2f34f213a0ae4af8c6a350e5717d00d0cc49683",
    "wiktionary_upstream_sha256": "2fa05a70de03fc0d8a3855a214e0b56c6087078571eb39173da4acb54df87e68",
    "built_at": "2026-09-09T15:55:18.948950+00:00",
    "counts": {"entries": 194171, "senses": 257911},
    "review_inputs": {
        "exam_tag_index_sha256": "9b380aab7fe6a5ba7475a36d8058fe87a45e82ec914d301c8d342fd4088163f6",
        "pinyin_candidates_sha256": "914f6894fff1f6033af6d8bb9858f6901aa2d1a960cd2afd8923f899584f1290",
        "ecdict_csv_sha256": "1a6947e04785db63613a92e14903cdae7954f7e84860b10e68e5c7cbb3f9c3cf",
        "english_uk_ipa_sha256": "221394caef0cf723b4f2df81a98ac33191293257b88aed5b1fb89466d3a0dc77",
        "english_us_ipa_sha256": "2af6f154a5c363275f052d1f85acedef38ed185ca9745aa4314be77f6b70de67",
    },
    "purpose": "Candidate discovery only. Every adopted mapping is pinned to its canonical English Wiktionary page revision in the review file.",
    "license": "Wiktionary-derived CC BY-SA 4.0 data; builder software license does not apply to generated data.",
}


def generate():
    return build_payloads(
        curation_path=CURATION,
        output_path=OUTPUT,
        manifest_path=MANIFEST,
        batch_name="02-wiktionary-2",
        prior_runtime_paths=PRIOR,
        source_snapshot=DISCOVERY_SNAPSHOT,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write generated data and manifest")
    args = parser.parse_args()
    outputs, manifest = generate()
    for path, payload in outputs.items():
        if args.apply:
            path.write_bytes(payload)
        elif not path.is_file() or path.read_bytes() != payload:
            raise SystemExit(f"Generated file differs; run with --apply: {path}")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
