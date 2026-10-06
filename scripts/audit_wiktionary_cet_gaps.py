"""Audit remaining CET gaps against English Wiktionary's Chinese translations.

This is a review-only acquisition step. It writes fetched pages and candidates
under ignored ``build/`` and never changes shipped vocabulary data. Wiktionary
text is CC BY-SA 4.0 / GFDL; any adopted data needs separate attribution and
license handling, not the project's MIT dictionary license.
"""
from __future__ import annotations

import collections
import html
import json
import re
import time
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "vocabulary/data/batches/02-pending.json"
PINYIN = ROOT / "build/pinyin-candidates.tsv"
OUT = ROOT / "build/source-audit/wiktionary-cet-gaps"
API = "https://en.wiktionary.org/w/api.php"
USER_AGENT = "WordtrailVocabularyAudit/0.1 (https://github.com/dakaizigitup/wordtrail)"
PAGE_SIZE = 30
REQUEST_PAUSE_SECONDS = 1.1

HEADINGS = re.compile(r"^(={2,6})\s*(.*?)\s*\1\s*$")
TRANS_TOP = re.compile(r"\{\{trans-top\|([^}|]+)")
TERM_TEMPLATE = re.compile(
    r"\{\{t(?:\+|-)?\|(?P<lang>cmn(?:-(?:hans|hant))?|zh(?:-(?:cn|hans|hant))?)\|(?P<term>[^|}\n]+)",
    re.IGNORECASE,
)
POS = {
    "noun": "n.", "proper noun": "n.", "verb": "v.", "auxiliary verb": "v.",
    "adjective": "adj.", "adverb": "adv.",
}


def clean_term(raw: str) -> str:
    term = html.unescape(raw.strip())
    term = re.sub(r"\[\[([^]|]+)\|([^]]+)\]\]", r"\2", term)
    term = re.sub(r"\[\[([^]]+)\]\]", r"\1", term)
    term = re.sub(r"''+", "", term)
    term = re.sub(r"<[^>]*>", "", term)
    term = term.replace("&nbsp;", " ").strip()
    return term


def fetch_titles(titles: list[str], cache_path: Path) -> dict:
    params = urlencode({
        "action": "query", "prop": "revisions", "rvprop": "content|ids|timestamp",
        "rvslots": "main", "titles": "|".join(titles), "format": "json",
        "formatversion": "2",
    })
    request = Request(API + "?" + params, headers={"User-Agent": USER_AGENT})
    last_error = None
    for attempt in range(4):
        try:
            with urlopen(request, timeout=45) as response:
                body = response.read()
            cache_path.write_bytes(body)
            return json.loads(body)
        except Exception as error:  # network failures are retried, then surfaced
            last_error = error
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Wiktionary API request failed for {len(titles)} titles") from last_error


def translation_rows(page: dict):
    revisions = page.get("revisions") or []
    if not revisions:
        return
    revision = revisions[0]
    text = revision.get("slots", {}).get("main", {}).get("content", "")
    lines = text.splitlines()
    in_english = False
    current_pos = ""
    index = 0
    while index < len(lines):
        match = HEADINGS.match(lines[index])
        if match:
            level, title = len(match.group(1)), match.group(2).strip()
            if level == 2:
                in_english = title.casefold() == "english"
                current_pos = ""
            elif in_english and title.casefold() in POS:
                current_pos = POS[title.casefold()]
            elif in_english and title.casefold() in {"etymology", "pronunciation", "alternative forms", "derived terms"}:
                current_pos = ""
            elif in_english and title.casefold() == "translations" and current_pos:
                translation_level = level
                index += 1
                sense = ""
                while index < len(lines):
                    nested = HEADINGS.match(lines[index])
                    if nested and len(nested.group(1)) <= translation_level:
                        index -= 1
                        break
                    top = TRANS_TOP.search(lines[index])
                    if top:
                        sense = top.group(1).strip()
                    if "{{trans-bottom" in lines[index]:
                        sense = ""
                    for term_match in TERM_TEMPLATE.finditer(lines[index]):
                        chinese = clean_term(term_match.group("term"))
                        if chinese:
                            yield {
                                "pos": current_pos,
                                "sense": sense,
                                "lang": term_match.group("lang").casefold(),
                                "chinese": chinese,
                            }
                    index += 1
        index += 1
    page["_audit_revision_id"] = revision.get("revid")
    page["_audit_timestamp"] = revision.get("timestamp")


def load_inputs():
    pending = json.loads(BATCH.read_text(encoding="utf-8"))["words"]
    words = sorted({row["word"] for row in pending})
    targets = {row["word"]: row["targets"] for row in pending}
    pinyin = {}
    for line in PINYIN.read_text(encoding="utf-8").splitlines():
        chinese, code, frequency = line.split("\t")
        pinyin[chinese] = (code, int(frequency))
    return words, targets, pinyin


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    words, targets, pinyin = load_inputs()
    pages = []
    for start in range(0, len(words), PAGE_SIZE):
        group = words[start:start + PAGE_SIZE]
        path = OUT / f"pages-{start // PAGE_SIZE + 1:02}.json"
        if path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8"))
        else:
            if start:
                time.sleep(REQUEST_PAUSE_SECONDS)
            payload = fetch_titles(group, path)
        pages.extend(payload.get("query", {}).get("pages", []))
        print(f"Fetched {min(start + len(group), len(words))}/{len(words)} CET headwords", flush=True)

    candidates = []
    words_with_page = set()
    words_with_chinese = set()
    for page in pages:
        word = page.get("title", "").casefold()
        if page.get("missing") or word not in targets:
            continue
        words_with_page.add(word)
        revisions = page.get("revisions") or []
        if not revisions:
            continue
        revision = revisions[0]
        page["_audit_revision_id"] = revision.get("revid")
        page["_audit_timestamp"] = revision.get("timestamp")
        for row in translation_rows(page) or []:
            words_with_chinese.add(word)
            chinese = row["chinese"]
            if chinese not in pinyin:
                continue
            code, frequency = pinyin[chinese]
            candidates.append({
                "word": word,
                "targets": ",".join(targets[word]),
                "pos": row["pos"],
                "chinese": chinese,
                "sense": row["sense"],
                "lang": row["lang"],
                "pinyin": code,
                "candidate_frequency": frequency,
                "page_id": page.get("pageid", ""),
                "revision_id": revision.get("revid", ""),
                "revision_timestamp": revision.get("timestamp", ""),
                "source_url": "https://en.wiktionary.org/wiki/" + quote(page.get("title", "").replace(" ", "_")),
            })

    unique = {}
    for row in candidates:
        key = (row["word"], row["pos"], row["chinese"], row["sense"])
        unique[key] = row
    candidates = sorted(unique.values(), key=lambda row: (row["word"], row["pos"], row["chinese"], row["sense"]))
    headers = ("word", "targets", "pos", "chinese", "sense", "lang", "pinyin",
               "candidate_frequency", "page_id", "revision_id", "revision_timestamp", "source_url")
    tsv = "\t".join(headers) + "\n" + "".join(
        "\t".join(str(row[key]).replace("\t", " ").replace("\n", " ") for key in headers) + "\n"
        for row in candidates
    )
    (OUT / "pinyin-reachable-candidates.tsv").write_text(tsv, encoding="utf-8", newline="\n")
    summary = {
        "source": "English Wiktionary via MediaWiki API",
        "source_license": "CC BY-SA 4.0 / GFDL; adopted records need separate attribution and license handling",
        "api": API,
        "pending_cet_headwords": len(words),
        "pages_found": len(words_with_page),
        "words_with_chinese_translation_sections": len(words_with_chinese),
        "pinyin_reachable_candidate_rows": len(candidates),
        "pinyin_reachable_unique_headwords": len({row["word"] for row in candidates}),
        "pinyin_reachable_unique_chinese_keys": len({row["chinese"] for row in candidates}),
        "pages_with_translations_but_no_exact_pinyin_candidate": len(words_with_chinese - {row["word"] for row in candidates}),
        "caveat": "Candidates are sourced from sense-grouped Wiktionary translations and exact Qingjian pinyin keys; they still require POS/sense review and do not modify shipped data.",
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
