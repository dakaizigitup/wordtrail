"""Verify the published CC-CEDICT tranche without research-only source caches."""
import csv
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "vocabulary/data"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CedictBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((DATA / "cccedict-manifest.json").read_text(encoding="utf-8"))
        cls.runtime = (DATA / "cccedict-expansion.tsv").read_bytes()
        with (DATA / "batches/04-cc-cedict-reviewed.tsv").open(encoding="utf-8", newline="") as stream:
            cls.reviewed = list(csv.DictReader(stream, delimiter="\t"))

    def test_runtime_payload_matches_separately_licensed_manifest(self):
        self.assertEqual(len(self.runtime.splitlines()), 58)
        self.assertEqual(self.manifest["runtime_file"]["rows"], 58)
        self.assertEqual(self.manifest["runtime_file"]["sha256"], digest(DATA / "cccedict-expansion.tsv"))
        self.assertEqual(self.manifest["curation_file"]["sha256"], digest(DATA / "batches/04-cc-cedict-reviewed.tsv"))
        self.assertEqual(self.manifest["source"]["sha256"], "8172061b2a647dd8a179788830ef233944baee479bc7018f111064ad16d8f46f")
        self.assertIn("CC BY-SA 4.0", self.manifest["license_boundary"])

    def test_each_runtime_row_has_an_exact_audit_record_and_exam_tags(self):
        runtime = [line.split("\t") for line in self.runtime.decode("utf-8").splitlines()]
        self.assertEqual(len(runtime), len(self.reviewed))
        for values, review in zip(runtime, self.reviewed):
            chinese, english, pos, source = values
            self.assertEqual((chinese, english, pos), (review["chinese"], review["word"], review["pos"]))
            self.assertEqual(source, "CC-CEDICT CC BY-SA 4.0")
            self.assertIn(review["target_tags"].split(",")[0], {"cet4", "cet6"})
            self.assertTrue(review["source_line"].isdigit())
            self.assertTrue(review["review_note"])
            self.assertGreaterEqual(int(review["pinyin_frequency"]), 1000)
            self.assertIn("a9aea223269eb9820590e5bca783eb299c317439", review["source_url"])

    def test_coverage_and_deferred_queue_are_explicit(self):
        self.assertEqual(self.manifest["added_pairs"], 58)
        self.assertEqual(self.manifest["added_headwords"], 58)
        self.assertEqual(self.manifest["added_candidate_keys"], 57)
        self.assertEqual(self.manifest["pending_cet_headwords_before"], 636)
        self.assertEqual(self.manifest["pending_cet_headwords_after"], 578)
        self.assertEqual(self.manifest["manual_reviewed_but_deferred_rows"], 66)
        self.assertEqual(self.manifest["coverage_after"]["cet4"]["mapped"], 4769)
        self.assertEqual(self.manifest["coverage_after"]["cet6"]["mapped"], 5552)


if __name__ == "__main__":
    unittest.main(verbosity=2)
