# Wiktionary vocabulary data attribution

The runtime supplements `wiktionary-expansion.tsv` and
`wiktionary-expansion-2.tsv` contain 22 manually reviewed English-to-Mandarin
mappings derived from English Wiktionary. Row-level entry links, pinned revision
IDs, source senses, and review notes are in:

- [`batches/03-wiktionary-reviewed.tsv`](batches/03-wiktionary-reviewed.tsv):
  15 mappings selected from English-to-Mandarin translation sections.
- [`batches/06-wiktionary-zh-reviewed.tsv`](batches/06-wiktionary-zh-reviewed.tsv):
  7 mappings selected from English glosses in Mandarin entries.

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

Changes made: selected exam-tagged headwords with a directly supported Mandarin
sense, compatible part of speech, an exact existing Qingjian pinyin key, and a
bundled IPA entry; normalized the selected pairs into compact TSV files. ECDICT
was used as an independently pinned sense/POS cross-check. The mappings do not
replace existing translations or reorder Chinese candidates.

The two runtime files and their row-level curation records are CC BY-SA 4.0
data. Adaptations of this Wiktionary-derived data must retain attribution, link
to the license, state changes, and use the same license. This notice applies
only to these four Wiktionary-derived data files. It does not change the
licenses of the software or the separately sourced ECDICT, KyleBing, or
CC-CEDICT data.
