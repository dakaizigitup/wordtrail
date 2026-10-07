# Wiktionary vocabulary data attribution

The runtime supplements `wiktionary-expansion.tsv` and
`wiktionary-expansion-2.tsv` contain 22 manually reviewed English-to-Mandarin
mappings derived from English Wiktionary. Row-level entry links, pinned revision
IDs, source senses, and review notes are in:

- [`batches/03-wiktionary-reviewed.tsv`](batches/03-wiktionary-reviewed.tsv):
  15 mappings selected from English-to-Mandarin translation sections.
- [`batches/06-wiktionary-zh-reviewed.tsv`](batches/06-wiktionary-zh-reviewed.tsv):
  7 mappings selected from English glosses in Mandarin entries.

The first professional-domain tranche adds 10 reviewed medical mappings in
`professional-expansion.tsv` and a compact, independently selectable topic index
in `professional-domain-tags.tsv` (computer, business, and medical). Exact
Chinese-English pairs, pinyin-candidate reachability, source sense IDs, and
whether a mapping was already present or added in this tranche are recorded in
[`batches/14-professional-domain-evidence.tsv`](batches/14-professional-domain-evidence.tsv).
The accept/reject decisions, including the rejected ambiguous candidate, are in
[`batches/14-professional-reviewed.tsv`](batches/14-professional-reviewed.tsv);
the pinned inputs and output hashes are in
[`professional-vocabulary-manifest.json`](professional-vocabulary-manifest.json).

Attribution: **English Wiktionary contributors**, [English Wiktionary](https://en.wiktionary.org/wiki/Main_Page).
Wiktionary entry text is available under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
and GFDL; this project distributes the selected data under CC BY-SA 4.0.

The second tranche used the fixed `lexhint-zh-english-dictionary-s10-2026.09.09`
artifact from [lexhint-datasets](https://github.com/buchwandler/lexhint-datasets)
only to discover candidates. Its compressed artifact SHA-256 is
`1bc71e741f884c3ef9ac801397b3dabfbf39ecd3ba666ca08d8a4206eaf114ac`; its
uncompressed SHA-256 is
`98fef9ba82047d0eaba650c1da074810c135da3c90e1fdb59f2faf197d6b7dd2`. The
underlying English Wiktionary Chinese-language split SHA-256 is
`adc32196f47344c894a83fb2d2f34f213a0ae4af8c6a350e5717d00d0cc49683`.

Changes made: the earlier batches selected exam-tagged headwords with a directly
supported Mandarin sense, compatible part of speech, an exact existing Qingjian
pinyin key, and bundled IPA. The professional batch selects exact domain-tagged
Chinese-English terms only when the Chinese key is an actual pinyin candidate;
new mappings additionally require a same-POS complete ECDICT gloss, a bundled
IPA entry, and manual review. Traditional source headwords are normalized to
simplified Chinese. Existing translations are retained and Chinese candidate
order is unchanged.

The Wiktionary expansion files, professional-domain tag index, and associated
row-level curation/evidence records are CC BY-SA 4.0 data. Adaptations of this
Wiktionary-derived data must retain attribution, link to the license, state
changes, and use the same license. This notice applies only to those
Wiktionary-derived data files; it does not change the licenses of the software
or separately sourced ECDICT, KyleBing, or CC-CEDICT data.
