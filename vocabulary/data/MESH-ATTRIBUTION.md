# NLM MeSH 2026 medical vocabulary tranche

## Source and terms

The English medical-topic names and descriptor hierarchy in this tranche come
from the U.S. National Library of Medicine (NLM), **Medical Subject Headings
(MeSH) 2026 Descriptor XML**:

- Download: <https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/xmlmesh/desc2026.zip>
- NLM download information: <https://www.nlm.nih.gov/databases/download/mesh.html>
- NLM MeSH terms and conditions: <https://www.nlm.nih.gov/databases/download/terms_and_conditions_mesh.html>
- Included source archive: [`sources/mesh/desc2026.zip`](sources/mesh/desc2026.zip)
- Archive SHA-256: `bb73dfdfe78cbfcd692ef399bb6df24750327ff62c4f53574826c56ba3d6a3f3`

NLM permits use and redistribution of MeSH data without a usage fee when NLM
is acknowledged and the version is identified. This project identifies NLM and
the 2026 version here and in the generated notices. MeSH is an NLM product; this
independent project is not endorsed by NLM. Only the English Descriptor XML is
used. No MeSH translation/MTMS files are included; NLM's general MeSH terms do
not cover those translation files.

## Selection and changes

The source supplies English descriptor names, synonyms and tree numbers. It
does not supply the Chinese mappings used by this project. The medical scope
includes descriptors with tree numbers under A, C, D, E, F, G and N; the G17
mathematics branch is excluded. The runtime tag list uses preferred descriptor
names only, avoiding synonym expansion that would make category labels broader
and less predictable.

New Chinese-to-English mappings require an exact ECDICT MIT short gloss and
part of speech, a local pinyin candidate, local English IPA, remaining
per-Chinese-key capacity, and an explicit review decision. ECDICT provides the
Chinese gloss and POS; MeSH provides the English medical concept and scope.
ECDICT license and attribution details are in [`ECDICT-LICENSE`](ECDICT-LICENSE)
and the root `NOTICE.txt`.

The fixed local inputs produced 256 candidate mappings. The reviewed tranche
accepts 75 mappings across 74 new English headwords, rejects 7 clear false
matches, and defers 174 candidates whose general ECDICT gloss is not precise
enough to establish the MeSH sense. The exact inputs and decisions are retained
in:

- [`batches/21-mesh-medical-candidates.tsv`](batches/21-mesh-medical-candidates.tsv)
- [`batches/21-mesh-medical-reviewed.tsv`](batches/21-mesh-medical-reviewed.tsv)
- [`mesh-medical-manifest.json`](mesh-medical-manifest.json)

The runtime adds 1,079 new medical-tag memberships. These are MeSH preferred
English names that already have an exact local Chinese mapping reachable from
a real pinyin key, plus the newly accepted mapped headwords. Existing medical
memberships are not counted again. The row-level descriptor IDs, tree numbers
and matching Chinese keys are in
[`batches/21-mesh-medical-tags-evidence.tsv`](batches/21-mesh-medical-tags-evidence.tsv).

## Runtime boundary

The compiled runtime contains only the 75 short reviewed mappings and the
compact medical-tag index in `mesh-medical-expansion.tsv` and
`mesh-medical-tags.tsv`. It does not load the full XML, definitions, audit
tables, or source archive while typing. The tag is a topic-membership hint; it
does not claim complete medical vocabulary coverage, replace professional
terminology, or provide medical advice. No fixed denominator supports a
medical-coverage percentage.

Rebuild with `python scripts/build_mesh_medical_batch.py`. The builder validates
the archive hash, fixed upstream vocabulary inputs, candidate table, review
decisions and output hashes. It does not download data at build or runtime.
