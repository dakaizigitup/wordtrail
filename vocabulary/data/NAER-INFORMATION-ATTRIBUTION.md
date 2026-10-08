# National Academy for Educational Research Information Terms

This tranche uses the National Academy for Educational Research (NAER) dataset
*Information Terms - High School and Below*, dataset 15407. The official open-data
portal identifies NAER as the provider and lists the Open Government Data License,
version 1.0. The pinned source snapshot and portal metadata are stored in
`sources/naer/information-basic-terms-2026-08-12.csv` and
`sources/naer/information-basic-dataset.json`.

Attribution for this project:

> National Academy for Educational Research, 2026, *Information Terms - High
> School and Below* (dataset 15407; portal metadata updated 2026-08-12). Released
> under the Open Government Data License, version 1.0. Source:
> https://data.gov.tw/dataset/15407.

The license permits reproduction, distribution, adaptation, and sublicensing,
subject to its attribution requirements. This project preserves the provider,
dataset title and identifier, license, source link, snapshot hash, and the fact
that Traditional Chinese source terms were normalized to Simplified Chinese.
The mapping and category files contain only reviewed terms; the complete source
CSV is retained for reproducibility and is never read by the typing-time lookup.

The compact runtime data is in `naer-information-expansion.tsv` and
`naer-information-tags.tsv`. Candidate and review evidence is in
`batches/38-naer-information-prefilter.tsv`,
`batches/38-naer-information-candidates.tsv`,
`batches/38-naer-information-reviewed.tsv`, and
`batches/38-naer-information-tags-reviewed.tsv`; the pinned hashes and build
counts are in `naer-information-manifest.json`.
