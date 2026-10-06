"""Actual packed-data expansion, goal priority, all-sense commits and exposure."""
import hashlib,json,statistics,tempfile,time,unittest
from test_native import call,ROOT

class ExpansionTests(unittest.TestCase):
    def setUp(self):
        self.user=tempfile.TemporaryDirectory(prefix='wordtrail-expansion-')
        response=call(op='create',data_dir=str(ROOT/'data/generated'),user_dir=self.user.name)
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
        self.assertEqual([s['text'] for s in c['translation_senses'][:2]],['household','family'])
        households=next(s for s in c['translation_senses'] if s['text']=='households')
        self.assertTrue(any(t['id']=='ielts' for t in households['tags']))
        self.assertEqual(c['pronunciation']['word'],'household')
        self.assertTrue(c['translation_senses'][0]['translation_source'])
        self.assertTrue(any(t['id']=='cet6' and t['selected'] for t in c['translation_senses'][0]['tags']))
        self.assertEqual(self.action('translation',index=c['id'],revision=state['revision'])['commit'],'household')
    def test_openetymology_word_has_target_provenance_and_is_queryable(self):
        before=self.type('hezuo')
        candidate=next(c for c in before['candidates'] if c['text']=='合作')
        order=[c['text'] for c in before['candidates']]
        state=self.action('vocabulary',vocabulary_targets=['tem8'])
        self.assertEqual([c['text'] for c in state['candidates']],order)
        candidate=next(c for c in state['candidates'] if c['text']=='合作')
        sense=next(s for s in candidate['translation_senses'] if s['text']=='cooperation')
        self.assertTrue(any(t['id']=='tem8' and t['selected'] for t in sense['tags']))
        # The pinned OpenEtymology list places cooperation in TOEFL, while
        # TEM8 membership comes from the other pinned exam-wordlist sources.
        self.assertIn('OpenEtymology',next(t for t in sense['tags'] if t['id']=='toefl')['sources'])
        self.assertEqual(self.action('translation',index=candidate['id'],sense_index=sense['index'],revision=state['revision'])['commit'],'cooperation')
    def test_cc_cedict_translation_is_reachable_prioritized_tagged_and_pronounced(self):
        before = self.type('huanjing')
        candidate_order = [candidate['text'] for candidate in before['candidates']]
        self.assertIn('环境', candidate_order)
        state = self.action('vocabulary', vocabulary_targets=['cet6'])
        self.assertEqual([candidate['text'] for candidate in state['candidates']], candidate_order)
        candidate = next(candidate for candidate in state['candidates'] if candidate['text'] == '环境')
        sense = next(sense for sense in candidate['translation_senses'] if sense['text'] == 'ambient')
        self.assertEqual(sense['translation_source'], 'CC-CEDICT CC BY-SA 4.0')
        self.assertTrue(any(tag['id'] == 'cet6' and tag['selected'] for tag in sense['tags']))
        self.assertEqual(sense['pronunciation']['word'], 'ambient')
        self.assertEqual(self.action('translation', index=candidate['id'], sense_index=sense['index'], revision=state['revision'])['commit'], 'ambient')
    def test_low_frequency_cc_cedict_word_is_reachable_and_committable(self):
        state=self.type('touzhi')
        candidate=None
        for _ in range(80):
            candidate=next((c for c in state['candidates'] if c['text']=='投掷'),None)
            if candidate is not None:break
            state=self.action('next_page')
        self.assertIsNotNone(candidate)
        order=[c['text'] for c in state['candidates']]
        state=self.action('vocabulary',vocabulary_targets=['cet6'])
        self.assertEqual([c['text'] for c in state['candidates']],order)
        candidate=next(c for c in state['candidates'] if c['text']=='投掷')
        sense=next(s for s in candidate['translation_senses'] if s['text']=='hurl')
        self.assertEqual(sense['translation_source'],'CC-CEDICT CC BY-SA 4.0')
        self.assertTrue(any(tag['id']=='cet6' and tag['selected'] for tag in sense['tags']))
        self.assertEqual(sense['pronunciation']['word'],'hurl')
        self.assertEqual(self.action('translation',index=candidate['id'],sense_index=sense['index'],revision=state['revision'])['commit'],'hurl')
    def test_batch_12_new_pinyin_key_is_reachable_tagged_and_prioritized(self):
        state=self.type('yiyanghuawu')
        candidate=None
        for _ in range(state['page_count']):
            candidate=next((item for item in state['candidates'] if item['text']=='一氧化物'),None)
            if candidate is not None:break
            state=self.action('next_page')
        self.assertIsNotNone(candidate)
        chinese_order=[item['text'] for item in state['candidates']]
        state=self.action('vocabulary',vocabulary_targets=['toefl'])
        self.assertEqual([item['text'] for item in state['candidates']],chinese_order)
        candidate=next(item for item in state['candidates'] if item['text']=='一氧化物')
        sense=next(item for item in candidate['translation_senses'] if item['text']=='monoxide')
        self.assertEqual(sense['translation_source'],'ECDICT MIT')
        self.assertTrue(any(tag['id']=='toefl' and tag['selected'] for tag in sense['tags']))
        self.assertEqual(sense['pronunciation']['word'],'monoxide')
        self.assertEqual(self.action('translation',index=candidate['id'],sense_index=sense['index'],revision=state['revision'])['commit'],'monoxide')
    def test_batch_13_pinyin_overlay_reaches_existing_exam_gloss(self):
        before=self.type('bupingdeng')
        candidate=next(item for item in before['candidates'] if item['text']=='不平等')
        chinese_order=[item['text'] for item in before['candidates']]
        state=self.action('vocabulary',vocabulary_targets=['toefl'])
        self.assertEqual([item['text'] for item in state['candidates']],chinese_order)
        candidate=next(item for item in state['candidates'] if item['text']=='不平等')
        sense=next(item for item in candidate['translation_senses'] if item['text']=='unequal')
        self.assertTrue(any(tag['id']=='toefl' and tag['selected'] for tag in sense['tags']))
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
    def test_batch_13_overlay_matches_its_pinned_manifest(self):
        path=ROOT/'vocabulary/data/pinyin-overlays/exam-target-batch-13.tsv'
        manifest=json.loads((ROOT/'vocabulary/data/exam-target-batch-13-manifest.json').read_text(encoding='utf-8'))
        rows=[line.split('\t') for line in path.read_text(encoding='utf-8').splitlines()]
        record=manifest['outputs']['exam-target-batch-13.tsv']
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),record['sha256'])
        self.assertEqual(len(rows),record['rows'])
        self.assertEqual(len(rows),407)
        self.assertEqual(len({row[0] for row in rows}),len(rows))
        self.assertTrue(all(2<=len(row[0])<=6 and all('\u3400'<=char<='\u9fff' for char in row[0]) for row in rows))
        self.assertTrue(all(row[2]=='0' for row in rows))
        self.assertTrue(all(row[3] in {'CC-CEDICT CC BY-SA 4.0','Rime ICE GPL-3.0','CC-CEDICT CC BY-SA 4.0 + Rime ICE GPL-3.0'} for row in rows))

def benchmark():
    with tempfile.TemporaryDirectory() as user:
        h=call(op='create',data_dir=str(ROOT/'data/generated'),user_dir=user)['handle'];results=[]
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
