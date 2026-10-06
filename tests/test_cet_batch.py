"""批次01数据保留、释义边界、覆盖统计及真实拼音候选的新增译词上屏。"""
import collections
import csv
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from test_native import ROOT, call

sys.path.insert(0, str(ROOT / 'scripts'))
from prepare_cet_batch import atomic_glosses, load_base, make_batch
from prepare_candidate_batch import kyle_glosses, make_batch as make_candidate_batch


class BatchDataTests(unittest.TestCase):
    def test_kyle_gloss_field_is_split_into_complete_short_senses(self):
        self.assertEqual(list(kyle_glosses('知道的， 意识到的；明白的')), ['知道的', '意识到的', '明白的'])
        self.assertEqual(list(kyle_glosses('person / place')), [])

    @classmethod
    def setUpClass(cls):
        cls.data = ROOT / 'vocabulary/data'
        cls.meta = json.loads((cls.data / 'expansion-manifest.json').read_text(encoding='utf-8'))
        cls.base = load_base(ROOT / 'build/expansion-base.tsv')
        cls.rows = [tuple(line.split('\t')) for line in (cls.data / 'english-expansion.tsv').read_text(encoding='utf-8').splitlines()]

    def test_all_published_pairs_and_their_order_are_retained(self):
        seed = collections.defaultdict(list)
        current = collections.defaultdict(list)
        for row in (self.data / 'batches/00-expansion.tsv').read_text(encoding='utf-8').splitlines():
            fields = tuple(row.split('\t'))
            seed[fields[0]].append(fields)
        for row in self.rows:
            current[row[0]].append(row)
        for chinese, old in seed.items():
            self.assertEqual(current[chinese][:len(old)], old, chinese)
        self.assertTrue(all(len(rows) <= 8 for rows in current.values()))
        self.assertEqual(len(self.rows), len({(r[0], r[1]) for r in self.rows}))
        batch01 = [tuple(line.split('\t')) for line in (self.data / 'batches/01-expansion.tsv').read_text(encoding='utf-8').splitlines()]
        self.assertEqual(self.rows[:len(batch01)], batch01)

    def test_gloss_parser_never_extracts_explanatory_substrings(self):
        base = {'勇敢': [], '勇敢的': [], '适当': [], '提高': []}
        glosses = list(atomic_glosses('a. 勇敢的, 适当的; 使人感到高兴的\\nv. 提高, 提高（水平）, [医] 提高', base))
        self.assertEqual(glosses, [('勇敢的', 'adj.'), ('适当', 'adj.'), ('提高', 'v.')])
        self.assertEqual(list(atomic_glosses('n. 同意\n[法] 同意\nadv. 在...旁边', base)), [('同意', 'n.')])

    def test_original_senses_without_pos_still_count_as_mapped(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'baseline.tsv'
            path.write_text('刷拉\t swish\n分析\tv. analyze\n', encoding='utf-8')
            base = load_base(path)
        self.assertEqual(base['刷拉'], [('swish', '')])
        self.assertEqual(base['分析'], [('analyze', 'v.')])

    def test_report_counts_exact_distinct_headwords_not_tag_sum(self):
        tags = {w: int(a) | int(b) for w, a, b in (r.split('\t') for r in (self.data / 'english-tags.tsv').read_text(encoding='utf-8').splitlines())}
        original = {w for senses in self.base.values() for w, _ in senses}
        seed = {r.split('\t')[1] for r in (self.data / 'batches/00-expansion.tsv').read_text(encoding='utf-8').splitlines()}
        after = original | {r[1] for r in self.rows}
        batch01_rows = [line.split('\t') for line in (self.data / 'batches/01-expansion.tsv').read_text(encoding='utf-8').splitlines()]
        after01 = original | {r[1] for r in batch01_rows}
        additions = [line.split('\t') for line in (self.data / 'batches/01-additions.tsv').read_text(encoding='utf-8').splitlines()]
        self.assertTrue(all(tags.get(row[1], 0) & 3 for row in additions))
        self.assertEqual(self.meta['batch01']['newly_mapped_headwords'], len(after01 - (original | seed)))
        self.assertEqual(self.meta['headwords_not_anywhere_in_original_glossary'], len({r[1] for r in self.rows} - original))
        for bit, code in enumerate(['cet4', 'cet6', 'tem4', 'tem8', 'toefl', 'ielts']):
            target = {w for w, mask in tags.items() if mask & (1 << bit)}
            self.assertEqual(self.meta['coverage_after'][code]['mapped'], len(target & after))
        pending = json.loads((self.data / 'batches/02-pending.json').read_text(encoding='utf-8'))['words']
        self.assertEqual({r['word'] for r in pending}, {w for w, mask in tags.items() if mask & 3} - after)
        self.assertTrue(all(r['candidate_reasons'] for r in pending))
        self.assertEqual(len(pending), self.meta['pending_distinct_cet_headwords'])
        reviewed = sum(1 for line in (self.data / 'batches/02-reviewed.tsv').read_text(encoding='utf-8').splitlines() if line and not line.startswith('#'))
        reviewed += sum(1 for line in (self.data / 'batches/02-reviewed-extended.tsv').read_text(encoding='utf-8').splitlines() if line and not line.startswith('#'))
        self.assertGreater(self.meta['batch02']['added_headwords'], 32)
        self.assertEqual(self.meta['batch02']['manual_reviewed_pairs'], reviewed)

    def test_reproducible_outputs_and_pinned_manifest(self):
        outputs, _ = make_candidate_batch(apply=True, check=True)
        for path, payload in outputs.items():
            self.assertEqual(path.read_bytes(), payload, str(path))
        data = (self.data / 'english-expansion.tsv').read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), self.meta['sha256'])
        self.assertNotIn('丰富\taffluent', data.decode('utf-8'))
        self.assertFalse(any('relinguish' == row[1] for row in self.rows))

    def test_wiktionary_batch_has_revision_pins_and_separate_license(self):
        manifest = json.loads((self.data / 'wiktionary-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['source']['license'].split(' (')[0], 'CC BY-SA 4.0')
        self.assertEqual(manifest['runtime_file']['rows'], 15)
        self.assertEqual(manifest['pending_before'] - manifest['pending_after'], 15)
        self.assertEqual(hashlib.sha256((self.data / 'wiktionary-expansion.tsv').read_bytes()).hexdigest(), manifest['runtime_file']['sha256'])
        with (self.data / 'batches/03-wiktionary-reviewed.tsv').open(encoding='utf-8', newline='') as stream:
            rows = list(csv.DictReader(stream, delimiter='\t'))
        self.assertEqual(len(rows), 15)
        for row in rows:
            self.assertRegex(row['source_revision_id'], r'^\d+$')
            self.assertTrue(row['source_url'].endswith('?oldid=' + row['source_revision_id']))
            self.assertTrue(row['review_note'])


class BatchNativeTests(unittest.TestCase):
    def setUp(self):
        self.user = tempfile.TemporaryDirectory(prefix='wordtrail-cet-batch-')
        result = call(op='create', data_dir=str(ROOT / 'data'), user_dir=self.user.name)
        self.assertIsNone(result['error'], result)
        self.handle = result['handle']

    def tearDown(self):
        call(op='destroy', handle=self.handle)
        self.user.cleanup()

    def action(self, op, **fields):
        result = call(op=op, handle=self.handle, **fields)
        self.assertIsNone(result['error'], result)
        return result['state']

    def typed(self, pinyin):
        self.action('reset')
        for char in pinyin:
            state = self.action('key', text=char)
        return state

    def test_new_noun_senses_have_correct_pos_ipa_tags_and_exact_commits(self):
        for pinyin, chinese, english in [('fenxi', '分析', 'analysis'), ('fazhan', '发展', 'development'),
                                         ('ziyou', '自由', 'freedom'), ('quexi', '缺席', 'absence'),
                                         ('jiechu', '接触', 'contact')]:
            state = self.typed(pinyin)
            candidates_before = [c['text'] for c in state['candidates']]
            chosen = next(c for c in state['candidates'] if c['text'] == chinese)
            if english != 'contact':
                original = [s['text'] for s in chosen['translation_senses'] if not s['translation_source']]
                self.assertTrue(original)
                added = next(s for s in chosen['translation_senses'] if s['text'] == english)
                self.assertEqual(added['translation_source'], 'Wordtrail-reviewed')
                self.assertEqual(added['part_of_speech'], 'n.')
                self.assertEqual(added['pronunciation']['word'], english)
                self.assertTrue(any(t['id'] in ['cet4', 'cet6'] for t in added['tags']))
            state = self.action('vocabulary', vocabulary_targets=['cet4', 'cet6'])
            self.assertEqual([c['text'] for c in state['candidates']], candidates_before)
            chosen = next(c for c in state['candidates'] if c['text'] == chinese)
            added = next(s for s in chosen['translation_senses'] if s['text'] == english)
            self.assertEqual(self.action('translation', index=chosen['id'], sense_index=added['index'], revision=state['revision'])['commit'], english)

    def test_clear_targets_preserves_original_first_sense_and_chinese_commit(self):
        state = self.typed('fenxi')
        chosen = next(c for c in state['candidates'] if c['text'] == '分析')
        self.assertEqual(chosen['translation_senses'][0]['text'], 'analyze')
        self.action('vocabulary', vocabulary_targets=['cet6'])
        state = self.action('vocabulary', vocabulary_targets=[])
        chosen = next(c for c in state['candidates'] if c['text'] == '分析')
        self.assertEqual(chosen['translation_senses'][0]['text'], 'analyze')
        self.assertEqual(self.action('select', index=chosen['id'], revision=state['revision'])['commit'], '分析')

    def test_wiktionary_additions_are_reachable_tagged_and_individually_committable(self):
        pinyin = {row.split('\t')[0]: row.split('\t')[1].replace(' ', '') for row in (ROOT / 'build/pinyin-candidates.tsv').read_text(encoding='utf-8').splitlines()}
        with (ROOT / 'vocabulary/data/batches/03-wiktionary-reviewed.tsv').open(encoding='utf-8', newline='') as stream:
            rows = list(csv.DictReader(stream, delimiter='\t'))
        for row in rows:
            chinese, english = row['chinese'], row['english']
            self.assertIn(chinese, pinyin)
            state = self.typed(pinyin[chinese])
            candidate = None
            for page in range(state['page_count']):
                candidate = next((item for item in state['candidates'] if item['text'] == chinese), None)
                if candidate is not None:
                    break
                state = self.action('next_page')
            self.assertIsNotNone(candidate, f'{chinese} is not reachable by its packed pinyin')
            candidate_order = [item['text'] for item in state['candidates']]
            state = self.action('vocabulary', vocabulary_targets=['cet4', 'cet6'])
            self.assertEqual([item['text'] for item in state['candidates']], candidate_order)
            candidate = next(item for item in state['candidates'] if item['text'] == chinese)
            sense = next((item for item in candidate['translation_senses'] if item['text'] == english), None)
            self.assertIsNotNone(sense, f'missing translated sense {chinese} -> {english}')
            self.assertEqual(sense['translation_source'], 'Wiktionary CC BY-SA 4.0')
            self.assertTrue(any(tag['id'] in {'cet4', 'cet6'} for tag in sense['tags']))
            self.assertEqual(sense['pronunciation']['word'], english)
            self.assertEqual(self.action('translation', index=candidate['id'], sense_index=sense['index'], revision=state['revision'])['commit'], english)


if __name__ == '__main__':
    unittest.main(verbosity=2)
