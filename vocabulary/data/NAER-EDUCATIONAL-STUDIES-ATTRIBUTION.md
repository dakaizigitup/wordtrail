# NAER Terminology of Educational Studies attribution

Source: National Academy for Educational Research, “Terminology of Educational Studies” (dataset 15367), listed on the [Taiwan Open Government Data Platform](https://data.gov.tw/en/datasets/15367). The platform describes English-Chinese educational terminology and lists the Open Government Data License v1.0 ([license](https://data.gov.tw/license)). The dataset page reports an update time of 2026-08-12 14:19.

The pinned CSV snapshot was retrieved on 2026-10-07. It contains 2,740 data records and has SHA-256 `6a72f8970c4e86999f53063866625df6852b93158b4a425b2a4bd0cab3b87d45`.

Changes: The project keeps only individually reviewed, concise English-Chinese noun mappings and compact source-membership tags. Mapping candidates must match an exact local ECDICT noun gloss, have local IPA, a reachable pinyin key, and available per-key capacity. The five accepted mappings were checked against the source context; ambiguous pairs are rejected or deferred with reasons. The 171 source-membership rows also require exact local noun, IPA, and pinyin evidence. They add to the existing education category and do not create a duplicate target or claim complete education vocabulary coverage.

The original source CSV, definitions, and examples are not read during typing. The runtime loads only the reviewed compact TSV files.

Audit artifacts and reproducible builder:

- `vocabulary/data/sources/naer/educational-studies-terms-2026-08-12.csv`
- `vocabulary/data/sources/naer/educational-studies-dataset.json`
- `vocabulary/data/naer-educational-studies-manifest.json`
- `vocabulary/data/batches/37-naer-educational-studies-prefilter.tsv`
- `vocabulary/data/batches/37-naer-educational-studies-reviewed.tsv`
- `vocabulary/data/batches/37-naer-educational-studies-tags-reviewed.tsv`
- `scripts/build_naer_educational_studies_batch.py`
