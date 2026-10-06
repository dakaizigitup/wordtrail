"""Actual packed-data expansion, goal priority, all-sense commits and exposure."""
import hashlib,json,statistics,tempfile,time,unittest
from test_native import call,ROOT

class ExpansionTests(unittest.TestCase):
    def setUp(self):
        self.user=tempfile.TemporaryDirectory(prefix='wordtrail-expansion-')
        response=call(op='create',data_dir=str(ROOT/'data'),user_dir=self.user.name)
        self.assertIsNone(response['error']);self.handle=response['handle']
    def tearDown(self):
        call(op='destroy',handle=self.handle);self.user.cleanup()
    def action(self,op,**fields):
        response=call(op=op,handle=self.handle,**fields)
        self.assertIsNone(response['error'],response);return response['state']
    def type(self,pinyin):
        self.action('reset')
        for char in pinyin:state=self.action('key',text=char)
        return state
    def test_real_new_translations_and_originals_are_retained(self):
        state=self.type('fangqi');c=next(c for c in state['candidates'] if c['text']=='放弃')
        senses=c['translation_senses'];self.assertEqual([s['text'] for s in senses[:2]],['give up','abandon'])
        added=next(s for s in senses if s['text']=='relinquish')
        self.assertEqual(added['translation_source'],'Wordtrail-reviewed')
        self.assertGreater(len(senses),2);self.assertLessEqual(len(senses),10)
        self.assertTrue(all(s['index']==i for i,s in enumerate(senses)))
        self.assertEqual(self.action('translation',index=c['id'],sense_index=added['index'],revision=state['revision'])['commit'],'relinquish')
    def test_added_cet6_word_becomes_first_without_chinese_reordering(self):
        before=self.type('yijiaren');state=self.action('vocabulary',vocabulary_targets=['cet6'])
        self.assertEqual([c['text'] for c in state['candidates']],[c['text'] for c in before['candidates']])
        c=next(c for c in state['candidates'] if c['text']=='一家人')
        self.assertEqual([s['text'] for s in c['translation_senses']],['household','family'])
        self.assertEqual(c['pronunciation']['word'],'household')
        self.assertTrue(c['translation_senses'][0]['translation_source'])
        self.assertTrue(any(t['id']=='cet6' and t['selected'] for t in c['translation_senses'][0]['tags']))
        self.assertEqual(self.action('translation',index=c['id'],revision=state['revision'])['commit'],'household')
    def test_original_selection_restores_and_non_english_has_no_expansion(self):
        self.type('yijiaren');self.action('vocabulary',vocabulary_targets=['cet6','tem8'])
        state=self.action('vocabulary',vocabulary_targets=[])
        self.assertEqual(next(c for c in state['candidates'] if c['text']=='一家人')['translation_senses'][0]['text'],'family')
        for lang in ['ja','es']:
            state=self.action('language',language=lang)
            self.assertTrue(all(s['translation_source'] is None for c in state['candidates'] for s in c['translation_senses']))
    def test_hidden_new_words_do_not_become_familiar_by_chinese_commits(self):
        for _ in range(35):
            state=self.type('fangqi');c=next(c for c in state['candidates'] if c['text']=='放弃')
            self.action('select',index=c['id'],revision=state['revision'])
        self.action('flush');state=self.type('fangqi');c=next(c for c in state['candidates'] if c['text']=='放弃')
        self.assertFalse(c['fresh'])
        self.assertTrue(next(s for s in c['translation_senses'] if s['text']=='relinquish')['fresh'])
    def test_pinned_manifest_matches_shipped_data(self):
        p=ROOT/'vocabulary/data/english-expansion.tsv';data=p.read_bytes()
        meta=json.loads((p.parent/'expansion-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256(data).hexdigest(),meta['sha256'])
        self.assertEqual(len(data.splitlines()),meta['added_translation_pairs'])
        self.assertNotIn(b'relinguish',data)
        self.assertNotIn('丰富\taffluent'.encode(),data)

def benchmark():
    with tempfile.TemporaryDirectory() as user:
        h=call(op='create',data_dir=str(ROOT/'data'),user_dir=user)['handle'];results=[]
        try:
            for pinyin in ['fangqi','zhongyao','yijiaren']:
                call(op='reset',handle=h)
                for c in pinyin:call(op='key',handle=h,text=c)
                for goals in [[],['cet6'],['cet4','cet6','tem4','tem8','toefl','ielts']]:
                    call(op='vocabulary',handle=h,vocabulary_targets=goals)
                    for _ in range(40):call(op='state',handle=h)
                    samples=[]
                    for _ in range(300):
                        t=time.perf_counter_ns();r=call(op='state',handle=h);samples.append((time.perf_counter_ns()-t)/1e6)
                        assert r['error'] is None
                    samples.sort();results.append(dict(pinyin=pinyin,goals=goals,p50_ms=statistics.median(samples),p95_ms=samples[285],p99_ms=samples[297]))
            (ROOT/'build/expansion-performance.json').write_text(json.dumps(dict(scope='Windows debug shared DLL C ABI, actual packed dictionary, expansion, tags, IPA and JSON decoding; not mobile latency',results=results),indent=2),encoding='utf-8')
        finally:call(op='destroy',handle=h)

if __name__=='__main__':
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ExpansionTests))
    if r.wasSuccessful():benchmark()
    raise SystemExit(0 if r.wasSuccessful() else 1)
