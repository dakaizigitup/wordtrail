# National Academy for Educational Research Management Academic Terms

This batch uses the National Academy for Educational Research (NAER) dataset *Management Academic Terms* (dataset 15440). The official metadata was updated on 2026-08-12. The pinned CSV snapshot is `vocabulary/data/sources/naer/management-academic-terms-2026-08-12.csv`, with SHA-256 `2f323ca6b4cf2a5a83dc01b1b044551c809e73f2f025858fd0b69c7b99e2bf4d`.

The dataset is released under the [Open Government Data License, version 1.0](https://data.gov.tw/license), which permits reproduction, distribution, adaptation, and sublicensing subject to attribution. Attribution:

> National Academy for Educational Research, 2026, *Management Academic Terms* (dataset 15440, metadata updated 2026-08-12). Released under the Open Government Data License, version 1.0. Source: https://data.gov.tw/dataset/15440.

Traditional Chinese source terms are converted to Simplified Chinese for exact matching. Runtime mappings are limited to reviewed one-word English terms with a local noun gloss, IPA, reachable pinyin key, and spare per-key capacity. A business membership is assigned only when the same English headword occurs in this management glossary and passes those local lexical checks. Source definitions and examples are not copied into the application; only compact reviewed TSV files enter the offline lookup.

See `vocabulary/data/naer-management-manifest.json`, the batch 33 review tables, and `scripts/build_naer_management_batch.py` for the snapshot, input hashes, individual mapping decisions, and reproducible build.
