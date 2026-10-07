# National Academy for Educational Research Computer Science Terms

The source snapshot is the National Academy for Educational Research's
*Cross-Strait Comparative Terminology - Computer Science* dataset, dataset
15275. The government open-data page identifies NAER as the provider, lists
the Traditional Chinese and Mainland Chinese term columns, and releases the
CSV under the Open Government Data License, version 1.0. The page metadata was
updated on 2026-08-12. See the [official dataset page](https://data.gov.tw/dataset/15275)
and [license](https://data.gov.tw/license).

Attribution for this project:

> National Academy for Educational Research, 2026, *Cross-Strait Comparative
> Terminology - Computer Science* (dataset 15275; portal metadata updated
> 2026-08-12). Released under the Open Government Data License, version 1.0.
> Source: https://data.gov.tw/dataset/15275.

The pinned CSV is retained with its metadata, SHA-256, and row references for
reproducibility. Traditional Chinese is converted to Simplified Chinese. A
runtime mapping is included only when the complete local Chinese gloss exactly
matches ECDICT, the English headword has local IPA, and the Chinese phrase is
an existing pinyin key. Every new mapping and every added computer-category
membership is reviewed for computing relevance. Definitions and long source
notes are not copied into the runtime lookup.

The runtime compiler loads only the reviewed compact TSVs. The full source,
candidate evidence, dispositions, hashes, and build command are recorded in
`computer-dataset.json`, `naer-computer-manifest.json`,
`batches/31-naer-computer-prefilter.tsv`,
`batches/31-naer-computer-candidates.tsv`,
`batches/31-naer-computer-reviewed.tsv`,
`batches/31-naer-computer-tags-reviewed.tsv`, and
`scripts/build_naer_computer_batch.py`.
