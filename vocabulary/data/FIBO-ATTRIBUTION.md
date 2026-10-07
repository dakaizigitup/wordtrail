# FIBO-derived business vocabulary attribution

The business-category tag tranche includes material from the Financial Industry Business Ontology (FIBO), maintained by the EDM Council.

- Upstream: <https://github.com/edmcouncil/fibo>
- Pinned commit: `9a7b90ccc64ef9df0762121ff058c9d27fd46037`
- License: MIT; the exact upstream `LICENSE` file is included at [`sources/fibo/LICENSE`](sources/fibo/LICENSE).
- Source snapshot: 52 RDF files containing selected finance/business class terms, pinned in [`sources/fibo/SNAPSHOT.json`](sources/fibo/SNAPSHOT.json). This is a partial snapshot, not the full FIBO ontology.
- Trademark: FIBO and the EDM Council name are not used as product branding or to imply endorsement.

## Modifications

We selected single-word English class labels that already have an English translation reachable from the local pinyin candidate set. We reviewed 87 eligible headwords, accepted 75 business/finance memberships and rejected 12. Of the accepted terms, 72 receive the business tag for the first time; three already had that tag from another source. This tranche changes category membership only: it adds no Chinese-English mappings, does not copy definitions into the runtime index, and does not reorder Chinese candidates. The evidence file preserves the selected FIBO class URIs and definitions for review under the upstream MIT license.

See the [batch manifest](fibo-business-manifest.json), [review evidence](batches/16-fibo-business-candidates.tsv), [accept/reject decisions](batches/16-fibo-business-reviewed.tsv), and [`fibo-business-tags.tsv`](fibo-business-tags.tsv). The extractor is [`build_fibo_business_batch.py`](../../scripts/build_fibo_business_batch.py).
