"""跨端真实内核的 C ABI 回归测试；使用随包完整词库而非模拟返回值。"""
from pathlib import Path
import ctypes, json, os, tempfile, unittest, time, statistics

ROOT=Path(__file__).resolve().parents[1]
TOOLS=Path(os.environ.get('WORDTRAIL_TOOLCHAIN','D:/soft/英语输入法/mobile-toolchain'))
DLL=ROOT/'target/debug/wordtrail_mobile.dll'
DIRECTORIES=[]
if os.name=='nt':
    for path in (TOOLS/'llvm-mingw-msvcrt').glob('*/bin'):
        DIRECTORIES.append(os.add_dll_directory(str(path)))
    rustbin=TOOLS/'rustup/toolchains/1.96.0-x86_64-pc-windows-gnu/lib/rustlib/x86_64-pc-windows-gnu/bin'
    DIRECTORIES.append(os.add_dll_directory(str(rustbin)))
LIB=ctypes.CDLL(str(DLL))
LIB.qjm_request.argtypes=[ctypes.c_char_p]
LIB.qjm_request.restype=ctypes.c_void_p
LIB.qjm_string_free.argtypes=[ctypes.c_void_p]

def call(**fields):
    pointer=LIB.qjm_request(json.dumps(fields,ensure_ascii=False).encode('utf-8'))
    try: return json.loads(ctypes.string_at(pointer).decode('utf-8'))
    finally: LIB.qjm_string_free(pointer)

class NativeTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory(prefix='wordtrail-test-')
        result=call(op='create',data_dir=str(ROOT/'data'),user_dir=self.directory.name)
        self.assertIsNone(result['error'],result)
        self.handle=result['handle']
    def tearDown(self):
        call(op='destroy',handle=self.handle)
        self.directory.cleanup()
    def action(self,op,**fields):
        result=call(op=op,handle=self.handle,**fields)
        self.assertIsNone(result['error'],result)
        return result['state']
    def type(self,text):
        state=None
        for char in text: state=self.action('key',text=char)
        return state
    def nihao(self):
        state=self.type('nihao')
        candidate=next(c for c in state['candidates'] if c['text']=='你好')
        return state,candidate
    def test_chinese_and_english_annotation(self):
        state,candidate=self.nihao()
        self.assertIn('hello',candidate['annotation'])
        self.assertTrue(candidate['fresh'])
        self.assertEqual(state['input'],'nihao')
        self.assertEqual(self.action('select',index=candidate['id'],revision=state['revision'])['commit'],'你好')
    def test_direct_translation(self):
        state,candidate=self.nihao()
        self.assertEqual(self.action('translation',index=candidate['id'],revision=state['revision'])['commit'],'hello')
    def test_independent_ipa_and_unmodified_commit(self):
        state,candidate=self.nihao()
        ipa=candidate['pronunciation']
        self.assertEqual(ipa['word'],'hello')
        self.assertTrue(ipa['uk'].startswith('/'))
        self.assertTrue(ipa['us'].startswith('/'))
        self.assertNotEqual(ipa['uk'],ipa['us'])
        self.assertNotIn(ipa['uk'],candidate['annotation'])
        self.assertEqual(self.action('translation',index=candidate['id'],revision=state['revision'])['commit'],'hello')
    def test_ipa_not_used_for_other_languages(self):
        self.nihao()
        for language in ('ja','es'):
            state=self.action('language',language=language)
            self.assertTrue(all(c['pronunciation'] is None for c in state['candidates']))
    def test_word_level_is_automatic_and_does_not_change_translation(self):
        state,candidate=self.nihao()
        self.assertEqual(candidate['vocabulary_levels'],[{'word':'hello','level':'A1'},{'word':'hi','level':'A1'}])
        self.assertTrue(candidate['annotation'].startswith('int. hello'))
        self.assertEqual(self.action('translation',index=candidate['id'],revision=state['revision'])['commit'],'hello')
    def test_individual_senses_have_distinct_levels(self):
        state=self.type('bbei')
        baby=next(c for c in state['candidates'] if c['text']=='宝贝')
        self.assertEqual(baby['vocabulary_levels'],[{'word':'baby','level':'A1'},{'word':'darling','level':'B2'}])
        self.assertEqual(self.action('select',index=baby['id'],revision=state['revision'])['commit'],'宝贝')
    def test_english_levels_do_not_leak_into_japanese_or_spanish(self):
        self.nihao()
        for language in ('ja','es'):
            state=self.action('language',language=language)
            self.assertTrue(all(c['vocabulary_levels']==[] for c in state['candidates']))
    def test_stale_candidate_does_not_commit(self):
        state,candidate=self.nihao()
        self.action('key',text='a')
        result=call(op='select',handle=self.handle,index=candidate['id'],revision=state['revision'])
        self.assertIn('candidates changed',result['error'])
        self.assertEqual(self.action('state')['input'],'nihaoa')
    def test_backspace_and_reset(self):
        self.type('nihao')
        self.assertEqual(self.action('backspace')['input'],'niha')
        self.assertEqual(self.action('reset')['candidates'],[])
        self.assertTrue(self.action('backspace')['delete_backward'])
    def test_languages_are_exclusive(self):
        _,candidate=self.nihao()
        self.assertIn('hello',candidate['annotation'])
        state=self.action('language',language='es')
        self.assertEqual(state['language'],'es')
        self.assertIn('hola',next(c for c in state['candidates'] if c['text']=='你好')['annotation'])
        state=self.action('language',language='ja')
        self.assertEqual(state['language'],'ja')
        self.assertNotIn('hello',next(c for c in state['candidates'] if c['text']=='你好')['annotation'])
    def test_language_failure_preserves_work(self):
        self.type('nihao')
        self.assertIsNotNone(call(op='language',handle=self.handle,language='xx')['error'])
        self.assertEqual(self.action('state')['input'],'nihao')
    def test_private_input_leaves_no_learning(self):
        self.action('reset',private=True)
        state,candidate=self.nihao()
        self.action('select',index=candidate['id'],revision=state['revision'])
        self.action('flush')
        files=list(Path(self.directory.name).glob('*'))
        self.assertFalse(any(p.name=='input-log.jsonl' for p in files))
        for path in files: self.assertNotIn('hello',path.read_text(encoding='utf-8'))
    def test_familiarity_persists(self):
        for _ in range(35):
            state,candidate=self.nihao()
            self.action('select',index=candidate['id'],revision=state['revision'])
        self.action('flush')
        self.action('reset')
        _,candidate=self.nihao()
        self.assertFalse(candidate['fresh'])
        call(op='destroy',handle=self.handle)
        result=call(op='create',data_dir=str(ROOT/'data'),user_dir=self.directory.name)
        self.handle=result['handle']
        _,candidate=self.nihao()
        self.assertFalse(candidate['fresh'])
        self.assertTrue((Path(self.directory.name)/'user-vocab.tsv').is_file())
    def test_paging_and_select_snapshot(self):
        self.type('shi')
        state=self.action('next_page')
        self.assertGreater(state['page_count'],1)
        self.assertEqual(state['page'],1)
        candidate=state['candidates'][0]
        self.assertEqual(self.action('select',index=candidate['id'],revision=state['revision'])['commit'],candidate['text'])
    def test_english_punctuation_and_raw_return(self):
        self.action('toggle')
        self.assertEqual(self.action('key',text='A')['commit'],'A')
        self.assertEqual(self.action('key',text=',')['commit'],',')
        self.action('toggle')
        self.type('nihao')
        self.assertEqual(self.action('enter')['commit'],'nihao')
        self.assertEqual(self.action('key',text=',')['commit'],'，')
    def test_partial_commit_keeps_remaining_syllables(self):
        state=self.type('nihaoshijie')
        candidate=next(c for c in state['candidates'] if c['text']=='你好')
        remaining=self.action('select',index=candidate['id'],revision=state['revision'])
        self.assertEqual(remaining['commit'],'你好')
        self.assertEqual(remaining['input'],'shijie')
    def test_bad_requests_are_errors(self):
        self.assertIsNotNone(call(op='state',handle=123456789)['error'])
        self.assertIsNotNone(call(op='key',handle=self.handle,text='abc')['error'])
        self.assertIsNotNone(call(op='create',data_dir='',user_dir='')['error'])

if __name__=='__main__':
    unittest.main(verbosity=2)
