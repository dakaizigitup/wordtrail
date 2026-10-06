"""Real shared-core reachability and commits for batch02 candidate mappings."""
import collections
import sys
import tempfile
import unittest
from pathlib import Path

from test_native import ROOT, call


class CandidateBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = [line.split('\t') for line in
                    (ROOT / 'vocabulary/data/batches/02-additions.tsv').read_text(encoding='utf-8').splitlines()]
        cls.pinyin = {}
        for line in (ROOT / 'build/pinyin-candidates.tsv').read_text(encoding='utf-8').splitlines():
            chinese, code, _ = line.split('\t')
            cls.pinyin[chinese] = code.replace(' ', '')

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='wordtrail-batch02-')
        created = call(op='create', data_dir=str(ROOT / 'data'), user_dir=self.directory.name)
        self.assertIsNone(created['error'], created)
        self.handle = created['handle']

    def tearDown(self):
        call(op='destroy', handle=self.handle)
        self.directory.cleanup()

    def action(self, op, **fields):
        result = call(op=op, handle=self.handle, **fields)
        self.assertIsNone(result['error'], result)
        return result['state']

    def type_code(self, pinyin):
        self.action('reset')
        state = None
        for char in pinyin:
            state = self.action('key', text=char)
        return state

    def find_candidate(self, state, chinese):
        for _ in range(state['page_count']):
            found = next((row for row in state['candidates'] if row['text'] == chinese), None)
            if found:
                return state, found
            state = self.action('next_page')
        self.fail('Pinyin candidate was not reachable: ' + chinese)

    def test_every_reviewed_word_is_reachable_and_committable(self):
        self.assertEqual(len(self.rows), 32)
        for chinese, english, pos, _source in self.rows:
            with self.subTest(chinese=chinese, english=english):
                self.action('vocabulary', vocabulary_targets=[])
                state, candidate = self.find_candidate(self.type_code(self.pinyin[chinese]), chinese)
                before_order = [row['text'] for row in state['candidates']]
                sense = next((row for row in candidate['translation_senses'] if row['text'] == english), None)
                self.assertIsNotNone(sense)
                self.assertEqual(sense['part_of_speech'], pos)
                self.assertEqual(sense['translation_source'], 'Wordtrail-batch02-reviewed')
                self.assertTrue(any(tag['id'] in ('cet4', 'cet6') for tag in sense['tags']))

                prioritized = self.action('vocabulary', vocabulary_targets=['cet4', 'cet6'])
                _, prioritized_candidate = self.find_candidate(prioritized, chinese)
                self.assertEqual([row['text'] for row in prioritized['candidates']], before_order)
                selected = next(row for row in prioritized_candidate['translation_senses'] if row['text'] == english)
                committed = self.action('translation', index=prioritized_candidate['id'],
                                        sense_index=selected['index'], revision=prioritized['revision'])
                self.assertEqual(committed['commit'], english)


if __name__ == '__main__':
    unittest.main(verbosity=2)
