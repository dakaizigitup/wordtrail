"""Shared exam-tag loading for offline vocabulary audits.

The base ECDICT/KyleBing index stays independently pinned. OpenEtymology list
membership is merged as a separate, separately licensed source at audit time.
"""
from pathlib import Path


def load_exam_tags(data_dir: Path) -> dict[str, int]:
    tags: dict[str, int] = {}
    for line in (data_dir / "english-tags.tsv").read_text(encoding="utf-8").splitlines():
        word, ecdict, kylebing = line.split("\t")
        tags[word] = int(ecdict) | int(kylebing)
    open_tags = data_dir / "openetymology-exam-tags.tsv"
    if open_tags.exists():
        for line in open_tags.read_text(encoding="utf-8").splitlines():
            word, mask = line.split("\t")
            tags[word] = tags.get(word, 0) | int(mask)
    wordlevel_tags = data_dir / "wordlevel-toefl-ielts-tags.tsv"
    if wordlevel_tags.exists():
        for line in wordlevel_tags.read_text(encoding="utf-8").splitlines():
            word, mask, _source = line.split("\t")
            tags[word] = tags.get(word, 0) | int(mask)
    return tags


RUNTIME_EXPANSIONS = (
    "english-expansion.tsv",
    "wiktionary-expansion.tsv",
    "wiktionary-expansion-2.tsv",
    "cccedict-expansion.tsv",
    "cccedict-expansion-2.tsv",
    "cccedict-expansion-3.tsv",
    "cccedict-expansion-4.tsv",
    "exam-target-ecdict-expansion.tsv",
    "exam-target-kylebing-expansion.tsv",
    "openetymology-exam-expansion.tsv",
    "exam-target-batch-11-ecdict-expansion.tsv",
    "exam-target-batch-11-kylebing-expansion.tsv",
    "exam-target-batch-11-dual-expansion.tsv",
    "exam-target-batch-11-cow-expansion.tsv",
    "exam-target-batch-11-koreader-cow-expansion.tsv",
    "exam-target-batch-11-cc-by-sa-expansion.tsv",
    "exam-target-batch-12-ecdict-expansion.tsv",
    "wordlevel-toefl-ielts-expansion.tsv",
)
