# CJK Computer Science Terms attribution

Attribution: dahlia and contributors, [CJK computer science terms comparison](https://github.com/dahlia/cjk-compsci-terms), pinned repository commit `3cf825e81375202fd408427933c3a30442defa4f`.

License: [Creative Commons Attribution-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-sa/4.0/). The upstream license text and the 28 pinned YAML tables used by this batch are retained under `sources/cjk-compsci-terms/`.

Changes made: selected entries from the upstream `zh-CN` tables, normalized traditional Chinese headwords to simplified Chinese with the project's pinned OpenCC conversion, and kept only exact Chinese keys present in the real local pinyin-candidate table. Existing English mappings receive a computing tag only when the source's component correspondences reconstruct the English headword. New single-word mappings require a local UK or US IPA entry, an ECDICT part-of-speech record, available per-key expansion capacity, and an explicit human accept/reject decision. This project adds selected English headwords as standalone Chinese-to-English candidate senses; it does not copy upstream definitions, examples, audio, Japanese, or Korean data.

The derived `cjk-compsci-tags.tsv`, `cjk-compsci-expansion.tsv`, reviewed decisions, and evidence are distributed under CC BY-SA 4.0. They are modifications of the cited upstream terminology table. The upstream snapshot hash, input hashes, output hashes, accepted/rejected counts, and scope limits are recorded in `cjk-compsci-manifest.json`.
