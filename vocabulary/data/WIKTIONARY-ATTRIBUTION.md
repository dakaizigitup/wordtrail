# Wiktionary vocabulary data attribution

`wiktionary-expansion.tsv` is a small, separately licensed data supplement. It
contains 15 manually reviewed English-to-Mandarin mappings selected from
English Wiktionary translation sections. The corresponding English entries,
Chinese translations, sense descriptions, and exact revision links are listed
in [`batches/03-wiktionary-reviewed.tsv`](batches/03-wiktionary-reviewed.tsv).

Attribution: **English Wiktionary contributors**, [English Wiktionary](https://en.wiktionary.org/wiki/Main_Page)
(individual entry links and revision IDs are provided in the reviewed TSV),
available under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
Wiktionary states that entry text is also available under the GNU Free
Documentation License; this supplement is distributed under the CC BY-SA 4.0
license option.

Changes made: selected CET4/CET6 headwords and Mandarin translations that match
an English sense, an existing Qingjian pinyin candidate, and a bundled IPA
entry; normalized the chosen mappings into a compact TSV. The curation file
also records review notes, source language, entry URL, page ID, revision ID,
and timestamp. No endorsement by Wiktionary or the Wikimedia Foundation is
implied.

The curation file and generated `wiktionary-expansion.tsv` are available under
CC BY-SA 4.0. Adaptations of this Wiktionary-derived data must retain the
attribution, link to the license, state changes, and use the same license.
This notice applies only to those two data files. It does not change the
licenses of the software or the separately sourced ECDICT and KyleBing data.
