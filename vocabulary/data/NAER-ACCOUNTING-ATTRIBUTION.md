# National Academy for Educational Research Accounting Terms

This batch uses the National Academy for Educational Research's *Accounting Academic Terms* dataset (dataset 15404). The Taiwan Open Data Platform metadata was updated on 2026-08-12. The pinned CSV snapshot is stored at `vocabulary/data/sources/naer/accounting-academic-terms-2026-08-12.csv` and has SHA-256 `46eaea4143811919253f94cd86062dcd49a9376bbe8ee85ac8c514a5d00a9869`.

The dataset is released under the [Open Government Data License, version 1.0](https://data.gov.tw/license), which permits reproduction, distribution, adaptation, and sublicensing subject to attribution. Attribution:

> National Academy for Educational Research, 2026, *Accounting Academic Terms* (dataset 15404, metadata updated 2026-08-12). Released under the Open Government Data License, version 1.0. Source: https://data.gov.tw/dataset/15404.

The project converts source Traditional Chinese to Simplified Chinese for exact local matching. It retains only reviewed concise English-Chinese mappings with local ECDICT noun evidence, IPA, a pinyin key, and available expansion capacity. Accounting category membership is added only for manually approved headwords that also have exact local Chinese, IPA, and pinyin evidence. Source definitions and examples are not copied into the application. Only the reviewed compact TSV files enter runtime lookup; the CSV is never scanned while typing.

See `vocabulary/data/naer-accounting-manifest.json`, the batch 32 review tables, and `scripts/build_naer_accounting_batch.py` for the snapshot metadata, hashes, filters, individual decisions, and reproducible build.
