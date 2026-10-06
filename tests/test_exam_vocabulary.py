"""Real shared engine regression: exam targets reorder senses, never Chinese candidates."""
import json, statistics, time, unittest, tempfile
from test_native import call, ROOT

class ExamVocabularyTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(prefix='wordtrail-exam-')
        result=call(op='create',data_dir=str(ROOT/'data'),user_dir=self.directory.name)
        self.assertIsNone(result['error']);self.handle=result['handle']
    def tearDown(self):
        call(op='destroy',handle=self.handle);self.directory.cleanup()
    def action(self,op,**fields):
        result=call(op=op,handle=self.handle,**fields)
        self.assertIsNone(result['error'],result);return result['state']
    def baby(self):
        self.action('reset')
        for c in 'bbei':state=self.action('key',text=c)
        return state,next(c for c in state['candidates'] if c['text']=='宝贝')
    def test_priority_ipa_levels_and_commit_are_consistent(self):
        original,baby=self.baby()
        self.assertEqual([s['text'] for s in baby['translation_senses']],['baby','darling'])
        state=self.action('vocabulary',vocabulary_targets=['tem4'])
        self.assertEqual([c['text'] for c in state['candidates']],[c['text'] for c in original['candidates']])
        reordered=next(c for c in state['candidates'] if c['text']=='宝贝')
        self.assertEqual([s['text'] for s in reordered['translation_senses']],['darling','baby'])
        self.assertEqual(reordered['pronunciation']['word'],'darling')
        self.assertEqual(reordered['vocabulary_levels'][0],dict(word='darling',level='B2'))
        tags=reordered['translation_senses'][0]['tags']
        self.assertEqual(tags[0]['id'],'tem4');self.assertTrue(tags[0]['selected'])
        self.assertGreater(len(tags),1);self.assertTrue(all(t['sources'] for t in tags))
        self.assertEqual(self.action('translation',index=reordered['id'],revision=state['revision'])['commit'],'darling')
    def test_secondary_sense_remains_available(self):
        self.action('vocabulary',vocabulary_targets=['tem4']);state,baby=self.baby()
        self.assertEqual(self.action('translation',index=baby['id'],sense_index=1,revision=state['revision'])['commit'],'baby')
    def test_multi_select_uses_or_and_preserves_ties(self):
        self.action('vocabulary',vocabulary_targets=['tem4','cet6']);state,baby=self.baby()
        self.assertEqual(state['vocabulary_targets'],['cet6','tem4'])
        self.assertEqual([s['text'] for s in baby['translation_senses']],['baby','darling'])
        state=self.action('vocabulary',vocabulary_targets=[])
        self.assertEqual(state['vocabulary_targets'],[])
        self.assertEqual([s['text'] for s in next(c for c in state['candidates'] if c['text']=='宝贝')['translation_senses']],['baby','darling'])
    def test_target_change_invalidates_snapshot_without_losing_composition(self):
        old,baby=self.baby();self.action('vocabulary',vocabulary_targets=['tem4'])
        result=call(op='translation',handle=self.handle,index=baby['id'],revision=old['revision'])
        self.assertIn('candidates changed',result['error']);self.assertEqual(self.action('state')['input'],'bbei')
    def test_invalid_selection_keeps_previous_targets(self):
        self.action('vocabulary',vocabulary_targets=['tem4'])
        result=call(op='vocabulary',handle=self.handle,vocabulary_targets=['unknown'])
        self.assertIn('unknown vocabulary',result['error']);self.assertEqual(self.action('state')['vocabulary_targets'],['tem4'])
    def test_other_languages_have_no_english_exam_tags(self):
        self.action('vocabulary',vocabulary_targets=['tem4']);self.baby()
        for language in ('ja','es'):
            state=self.action('language',language=language)
            for candidate in state['candidates']:
                self.assertTrue(all(s['tags']==[] and s['pronunciation'] is None for s in candidate['translation_senses']))
        state=self.action('language',language='en')
        self.assertEqual(next(c for c in state['candidates'] if c['text']=='宝贝')['translation_senses'][0]['text'],'darling')
    def test_chinese_commit_is_unchanged(self):
        self.action('vocabulary',vocabulary_targets=['tem4']);state,baby=self.baby()
        self.assertEqual(self.action('select',index=baby['id'],revision=state['revision'])['commit'],'宝贝')

def benchmark():
    with tempfile.TemporaryDirectory(prefix='wordtrail-perf-') as user:
        start=time.perf_counter_ns();response=call(op='create',data_dir=str(ROOT/'data'),user_dir=user)
        startup=(time.perf_counter_ns()-start)/1e6;handle=response['handle']
        try:
            for c in 'bbei':call(op='key',handle=handle,text=c)
            results=[]
            for targets in ([],['tem4'],['cet4','cet6','tem4','tem8','toefl','ielts']):
                call(op='vocabulary',handle=handle,vocabulary_targets=targets)
                for _ in range(40):call(op='state',handle=handle)
                samples=[]
                for _ in range(300):
                    start=time.perf_counter_ns();state=call(op='state',handle=handle);samples.append((time.perf_counter_ns()-start)/1e6);assert state['error'] is None
                samples.sort();results.append(dict(targets=targets,p50_ms=statistics.median(samples),p95_ms=samples[int(len(samples)*.95)],p99_ms=samples[int(len(samples)*.99)]))
            (ROOT/'build/exam-vocabulary-performance.json').write_text(json.dumps(dict(scope='Windows debug shared DLL via C ABI; real packed dictionary, tags, CEFR, IPA and JSON decode; not Android touch latency',startup_ms=startup,results=results),indent=2),encoding='utf-8')
        finally:call(op='destroy',handle=handle)

if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ExamVocabularyTests))
    if result.wasSuccessful():benchmark()
    raise SystemExit(0 if result.wasSuccessful() else 1)
