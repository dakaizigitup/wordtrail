# NAER Education Terminology attribution

Source: National Academy for Educational Research, “Education Terminology” (dataset 6319), as listed on the [Taiwan Open Government Data Platform](https://data.gov.tw/en/datasets/6319). The platform identifies the data as English-Chinese education terminology and lists the Open Government Data License v1.0 ([license](https://data.gov.tw/license)).

The pinned CSV snapshot was retrieved on 2026-10-07. It contains 2,198 data records and has SHA-256 `b674073b959c749546cac19ef867d27a908ee492d39f69cec4bc4c2dcdcaed57`.

Changes: The project keeps only individually reviewed English-Chinese noun mappings and compact source-membership tags. Mapping candidates must have an exact local ECDICT noun gloss, local IPA, a reachable pinyin key and available per-key capacity. The project excludes source definitions and longer explanations from runtime lookup. Education membership records that a headword appears in the source with local noun, IPA and pinyin evidence; it does not claim that every sense of the English headword is education-specific or that the category covers the entire field.

Audit artifacts and reproducible builder:

- `vocabulary/data/sources/naer/education-terminology-2026-06-01.csv`
- `vocabulary/data/sources/naer/education-dataset.json`
- `vocabulary/data/naer-education-manifest.json`
- `vocabulary/data/batches/35-naer-education-reviewed.tsv`
- `vocabulary/data/batches/35-naer-education-tags-reviewed.tsv`
- `scripts/build_naer_education_batch.py`
