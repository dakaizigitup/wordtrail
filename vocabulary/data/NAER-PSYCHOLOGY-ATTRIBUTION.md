# NAER Psychology Terminology attribution

Source: National Academy for Educational Research, “Psychology Terminology” (dataset 15167), listed on the [Taiwan Open Government Data Platform](https://data.gov.tw/en/datasets/15167). The platform describes English-Chinese psychology terminology and lists the Open Government Data License v1.0 ([license](https://data.gov.tw/license)).

The pinned CSV snapshot was retrieved on 2026-10-07. It contains 11,085 data records and has SHA-256 `d603fce3628389aa849c73f1af4104653357e715fb82946e35b67507d992f166`.

Changes: The project keeps individually reviewed, concise English-Chinese noun mappings and compact source-membership tags. Mapping candidates must match an exact local ECDICT noun gloss, have local IPA, a reachable pinyin key, and available per-key capacity. Ambiguous pairs are rejected or deferred with reasons. Psychology membership means that the headword occurs in this source and has exact local noun, IPA, and pinyin evidence; it does not mean every sense is psychology-specific or that this source is a complete psychology vocabulary.

The original source CSV, definitions, and examples are not read during typing. The runtime loads only the reviewed compact TSV files.

Audit artifacts and reproducible builder:

- `vocabulary/data/sources/naer/psychology-academic-terms-2026-08-12.csv`
- `vocabulary/data/sources/naer/psychology-dataset.json`
- `vocabulary/data/naer-psychology-manifest.json`
- `vocabulary/data/batches/36-naer-psychology-prefilter.tsv`
- `vocabulary/data/batches/36-naer-psychology-reviewed.tsv`
- `vocabulary/data/batches/36-naer-psychology-tags-reviewed.tsv`
- `scripts/build_naer_psychology_batch.py`
