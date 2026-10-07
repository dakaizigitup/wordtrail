# NAER Administration Academic Terms attribution

Source: National Academy for Educational Research, “Administration Academic Terms,” dataset 15262, as listed on the [Taiwan Open Government Data Platform](https://data.gov.tw/dataset/15262). The dataset is available under the Open Government Data License, version 1.0 ([license](https://data.gov.tw/license)).

The pinned CSV snapshot was retrieved on 2026-10-07. It contains 3,737 data records and has SHA-256 `8faf844b2393fbb27f432a8a5df8e4194c6e64c8a0c7754b0a6242a7b2e4f05b`.

Changes: The project keeps only reviewed English-to-Chinese mappings and a compact administration-domain membership list. A candidate must be a single-word English headword with an exact local ECDICT noun gloss, local IPA, an existing reachable pinyin key, and available per-key capacity. Each new mapping has an explicit review outcome. The source CSV, definitions, and longer explanations are not loaded during typing. The added category is labeled “行政学” and records membership in this source; it does not claim comprehensive coverage of public administration.

Audit artifacts and reproducible builder:

- `vocabulary/data/sources/naer/administration-academic-terms-2026-08-12.csv`
- `vocabulary/data/sources/naer/administration-dataset.json`
- `vocabulary/data/naer-administration-manifest.json`
- `vocabulary/data/batches/34-naer-administration-reviewed.tsv`
- `vocabulary/data/batches/34-naer-administration-tags-reviewed.tsv`
- `scripts/build_naer_administration_batch.py`
