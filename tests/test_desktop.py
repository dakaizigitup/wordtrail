"""Exercise the real Windows server over an isolated pipe and capture its candidate window."""
from pathlib import Path
import csv, ctypes, ctypes.wintypes as W, json, os, shutil, struct, subprocess, time
import tkinter as tk
from PIL import ImageGrab

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'build/desktop-test'
STAGE.mkdir(parents=True,exist_ok=True)
(STAGE/'data').mkdir(exist_ok=True)
shutil.copy2(ROOT/'target/release/qingjian-server.exe',STAGE/'qingjian-server.exe')
shutil.copy2(ROOT/'data/pronunciation-en.qj',STAGE/'data/pronunciation-en.qj')
for target,source in [(STAGE/'data/generated',Path('C:/Program Files/Qingjian/data/generated')),(STAGE/'assets',Path('C:/Program Files/Qingjian/assets'))]:
    if not target.exists():
        subprocess.run(['powershell.exe','-NoProfile','-Command',f"New-Item -ItemType Junction -Path '{target}' -Target '{source}' | Out-Null"],check=True)
USER=ROOT/'build/desktop-test-user'
config=USER/'roaming/Qingjian/config.toml'
config.parent.mkdir(parents=True,exist_ok=True)
config.write_text('[general]\nlearning_language="en"\nlayout="vertical"\n[model]\nenabled=false\n[predict]\nenabled=false\n[status_bar]\nenabled=false\n',encoding='utf-8')
vocabulary=config.with_name('wordtrail-vocabulary.json')
vocabulary.write_text('{"targets":[]}',encoding='utf-8')
PIPE=r'\\.\pipe\wordtrail-ipa-test'
env=dict(os.environ,APPDATA=str(USER/'roaming'),LOCALAPPDATA=str(USER/'local'),WORDTRAIL_TEST_PIPE=PIPE)
ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
background=tk.Tk()
background.title('词伴 · 隔离候选测试')
background.overrideredirect(True)
background.maxsize(8000,4000)
background.geometry('8000x4000+0+0');background.configure(bg='#edf4ef')
background.update();background.lift()
process=subprocess.Popen([str(STAGE/'qingjian-server.exe')],cwd=STAGE,env=env,creationflags=subprocess.CREATE_NO_WINDOW)
checks=[]
def check(name,value):
    assert value,name
    checks.append(name)
    print('PASS:',name,flush=True)
try:
    deadline=time.monotonic()+45
    while True:
        try: pipe=open(PIPE,'r+b',buffering=0);break
        except OSError:
            assert process.poll() is None,'Desktop server exited during startup'
            if time.monotonic()>deadline:raise TimeoutError('Server pipe unavailable')
            time.sleep(.2)
    def send(kind,payload,reply=True):
        encoded=json.dumps({kind:payload},ensure_ascii=False).encode()
        pipe.write(struct.pack('<I',len(encoded))+encoded)
        if not reply:return
        # A bounded read protects the test from protocol regressions.
        import concurrent.futures
        def read():
            header=pipe.read(4)
            assert len(header)==4,'Incomplete IPC header'
            remaining=struct.unpack('<I',header)[0];body=b''
            assert remaining<16*1024*1024
            while len(body)<remaining:body+=pipe.read(remaining-len(body))
            return json.loads(body)
        executor=concurrent.futures.ThreadPoolExecutor(1)
        try:return executor.submit(read).result(timeout=15)
        finally:executor.shutdown(wait=False)
    session=91821
    check('protocol 7 opens a session', 'SessionOpened' in send('OpenSession',dict(session=session,app='wordtrail-ipa-test.exe',protocol=7)))
    send('Privacy',dict(session=session,private=True),False)
    def key(char,ctrl=False,alt=False,shift=False):
        return send('Key',dict(session=session,event=dict(virtual_key=ord(char.upper()),character=char,modifiers=dict(ctrl=ctrl,shift=shift,alt=alt,win=False,caps=False,english_mode=False))))['KeyResult']
    for char in 'nihao':result=key(char)
    check('real dictionary produces Chinese candidate','你好' in json.dumps(result,ensure_ascii=False))
    send('PositionCandidates',dict(session=session,rect=dict(left=180,top=160,right=182,bottom=182)),False)
    user32=ctypes.WinDLL('user32',use_last_error=True)
    user32.SetProcessDpiAwarenessContext.argtypes=[ctypes.c_void_p]
    user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    CALLBACK=ctypes.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
    user32.GetWindowThreadProcessId.argtypes=[W.HWND,ctypes.POINTER(W.DWORD)]
    user32.GetClassNameW.argtypes=[W.HWND,W.LPWSTR,ctypes.c_int]
    user32.GetWindowRect.argtypes=[W.HWND,ctypes.POINTER(W.RECT)]
    user32.IsWindowVisible.argtypes=[W.HWND]
    def window():
        found=[]
        @CALLBACK
        def visit(hwnd,_):
            pid=W.DWORD();user32.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
            name=ctypes.create_unicode_buffer(256);user32.GetClassNameW(hwnd,name,256)
            if pid.value==process.pid and name.value=='QingjianCandidateWindow' and user32.IsWindowVisible(hwnd):
                rect=W.RECT();user32.GetWindowRect(hwnd,ctypes.byref(rect))
                if rect.right>rect.left and rect.bottom>rect.top:found.append((rect.left,rect.top,rect.right,rect.bottom))
            return True
        user32.EnumWindows(visit,0)
        return found[0] if found else None
    deadline=time.monotonic()+20
    while not (bounds:=window()):
        if time.monotonic()>deadline:raise TimeoutError('Candidate window did not appear')
        time.sleep(.2)
    time.sleep(1)
    screenshot=ROOT/'docs/screenshots/desktop-0.1.4-default.png'
    ImageGrab.grab(bbox=bounds).save(screenshot)
    check('native candidate window renders',screenshot.stat().st_size>1000)
    result=key('1',ctrl=True)
    check('translation commit contains only hello',result['commit']=='hello')
    for char in 'nihao':result=key(char)
    result=key(' ')
    check('normal Chinese commit is unchanged',result['commit']=='你好')
    for char in 'bbei':result=key(char)
    before=result['frame']['candidates']['items']
    vocabulary.write_text('{"targets":["tem4"]}',encoding='utf-8')
    time.sleep(1.2)
    updated=send('Poll',dict(session=session))['Update']['frame']['candidates']['items']
    check('target hot reload preserves Chinese candidate order',[c['text'] for c in before]==[c['text'] for c in updated])
    baby=next(c for c in updated if c['text']=='宝贝')
    check('real IPC frame prioritizes TEM4 darling while retaining baby',[s['text'] for s in baby['translation']['senses']]==['darling','baby'])
    send('PositionCandidates',dict(session=session,rect=dict(left=180,top=160,right=182,bottom=182)),False)
    time.sleep(.4)
    if (box:=window()):ImageGrab.grab(bbox=box).save(ROOT/'docs/screenshots/desktop-0.1.4-vocabulary.png')
    result=key(str(updated.index(baby)+1),ctrl=True)
    check('Ctrl digit inserts prioritized translation matching displayed frame',result['commit']=='darling')
    vocabulary.write_text('{"targets":[]}',encoding='utf-8');time.sleep(1.2)
    send('Poll',dict(session=session))
    for char in 'fangqi':result=key(char)
    expanded=result['frame']['candidates']['items']
    abandon=next(c for c in expanded if c['text']=='放弃')
    senses=abandon['translation']['senses']
    check('real IPC preserves originals and exposes actual added relinquish',senses[0]['text']=='give up' and senses[1]['text']=='abandon' and any(s['text']=='relinquish' for s in senses))
    slot=str(expanded.index(abandon)+1);seen=set()
    for _ in range(len(senses)):
        result=key(slot,ctrl=True,alt=True)
        current=result['frame']['candidates']['items']
        check_order=[c['text'] for c in current]==[c['text'] for c in expanded]
        assert check_order,'Chinese order changed during translation browsing'
        seen.update(s['text'] for s in next(c for c in current if c['text']=='放弃')['translation']['senses'][:2])
    check('all extra words can be browsed without changing Chinese order',len(seen)==len(senses))
    result=key(slot,ctrl=True,alt=True)
    current=next(c for c in result['frame']['candidates']['items'] if c['text']=='放弃')
    expected=current['translation']['senses'][0]['text']
    send('PositionCandidates',dict(session=session,rect=dict(left=180,top=160,right=182,bottom=182)),False);time.sleep(.4)
    if (box:=window()):ImageGrab.grab(bbox=box).save(ROOT/'docs/screenshots/desktop-0.1.4-expansion.png')
    check('Ctrl digit commits the currently browsed new word',key(slot,ctrl=True)['commit']==expected)
    vocabulary.write_text('{"targets":["cet6"]}',encoding='utf-8');time.sleep(1.2)
    send('Poll',dict(session=session))
    for char in 'yijiaren':result=key(char)
    family=next(c for c in result['frame']['candidates']['items'] if c['text']=='一家人')
    check('new CET6 household is prioritized before original family',[s['text'] for s in family['translation']['senses']]==['household','family'])
    check('new prioritized word commits through real IPC',key(str(result['frame']['candidates']['items'].index(family)+1),ctrl=True)['commit']=='household')
    vocabulary.write_text('{"targets":[]}',encoding='utf-8')
    for pinyin,chinese,english in [('fenxi','分析','analysis'),('fazhan','发展','development'),('ziyou','自由','freedom'),('quexi','缺席','absence')]:
        for char in pinyin:result=key(char)
        items=result['frame']['candidates']['items']
        c=next(c for c in items if c['text']==chinese)
        words=[s['text'] for s in c['translation']['senses']]
        check('batch01 real IPC '+chinese+' retains original and adds '+english,english in words and len(words)>1)
        before=[c['text'] for c in items];slot=str(items.index(c)+1)
        for _ in range(len(words)+1):
            c=next(c for c in items if c['text']==chinese)
            shown=[s['text'] for s in c['translation']['senses'][:2]]
            if english in shown:break
            result=key(slot,ctrl=True,alt=True);items=result['frame']['candidates']['items']
            assert [c['text'] for c in items]==before
        assert english in shown,'Added word not reachable in browsed display'
        check('batch01 current displayed '+english+' commits exactly',key(slot,ctrl=True,shift=shown.index(english)==1)['commit']==english)
    vocabulary.write_text('{"targets":["cet4","cet6"]}',encoding='utf-8');time.sleep(1.2)
    send('Poll',dict(session=session))
    for pinyin,chinese,english in [('ranshao','燃烧','combustion'),('xiandaihua','现代化','modernize'),('zhongli','中立','neutrality'),('weifan','违反','violation')]:
        for char in pinyin:result=key(char)
        items=result['frame']['candidates']['items']
        candidate=next(c for c in items if c['text']==chinese)
        senses=candidate['translation']['senses'];words=[sense['text'] for sense in senses]
        check('batch02 real IPC '+chinese+' retains original and adds '+english,len(words)>1 and english in words)
        before=[c['text'] for c in items];slot=str(items.index(candidate)+1);shown=[]
        for _ in range(len(senses)+1):
            candidate=next(c for c in items if c['text']==chinese)
            shown=[sense['text'] for sense in candidate['translation']['senses'][:2]]
            if english in shown:break
            result=key(slot,ctrl=True,alt=True);items=result['frame']['candidates']['items']
            assert [c['text'] for c in items]==before,'Chinese order changed while browsing batch02 translation'
        assert english in shown,'Batch02 word did not appear in the real candidate window'
        check('batch02 displayed '+english+' commits exactly',key(slot,ctrl=True,shift=shown.index(english)==1)['commit']==english)
    for pinyin,chinese,english,has_original in [('zuijin','最近','newly',True),('chuxian','出现','emergence',True),('zhidaode','知道的','aware',False)]:
        for char in pinyin:result=key(char)
        items=result['frame']['candidates']['items']
        candidate=next(c for c in items if c['text']==chinese)
        senses=candidate['translation']['senses'];words=[sense['text'] for sense in senses]
        check('batch02 extended real IPC '+chinese+' adds '+english,(len(words)>1 if has_original else len(words)>0) and english in words)
        before_candidates=[c['text'] for c in items]
        slot=str(items.index(candidate)+1);shown=[]
        for _ in range(len(senses)+1):
            candidate=next(c for c in items if c['text']==chinese)
            shown=[sense['text'] for sense in candidate['translation']['senses'][:2]]
            if english in shown:break
            result=key(slot,ctrl=True,alt=True);items=result['frame']['candidates']['items']
            assert [c['text'] for c in items]==before_candidates,'Chinese candidate order changed while browsing extended batch02'
        assert english in shown,'Extended batch02 word did not appear in the real candidate window'
        check('extended batch02 displayed '+english+' commits exactly',key(slot,ctrl=True,shift=shown.index(english)==1)['commit']==english)
    vocabulary.write_text('{"targets":["cet4","cet6"]}',encoding='utf-8');time.sleep(1.2)
    send('Poll',dict(session=session))
    pinyin_codes={line.split('\t')[0]:line.split('\t')[1].replace(' ','') for line in (ROOT/'build/pinyin-candidates.tsv').read_text(encoding='utf-8').splitlines()}
    with (ROOT/'vocabulary/data/batches/03-wiktionary-reviewed.tsv').open(encoding='utf-8',newline='') as stream:
        wiktionary_rows=list(csv.DictReader(stream,delimiter='\t'))
    for row in wiktionary_rows:
        for char in pinyin_codes[row['chinese']]:result=key(char)
        items=result['frame']['candidates']['items']
        for _ in range(80):
            candidate=next((c for c in items if c['text']==row['chinese']),None)
            if candidate is not None:break
            page=send('Key',dict(session=session,event=dict(virtual_key=9,character=None,modifiers=dict(ctrl=False,shift=False,alt=False,win=False,caps=False,english_mode=False))))['KeyResult']
            next_items=page['frame']['candidates']['items']
            if [c['text'] for c in next_items]==[c['text'] for c in items]:break
            result=page;items=next_items
        check('Wiktionary IPC '+row['chinese']+' exposes '+row['english'],candidate is not None and any(s['text']==row['english'] for s in candidate['translation']['senses']))
        before=[c['text'] for c in items];slot=str(items.index(candidate)+1);shown=[]
        for _ in range(len(candidate['translation']['senses'])+1):
            candidate=next(c for c in result['frame']['candidates']['items'] if c['text']==row['chinese'])
            shown=[s['text'] for s in candidate['translation']['senses'][:2]]
            if row['english'] in shown:break
            result=key(slot,ctrl=True,alt=True);items=result['frame']['candidates']['items']
            assert [c['text'] for c in items]==before,'Chinese order changed while browsing Wiktionary translation'
        assert row['english'] in shown,'Wiktionary word did not appear in the real candidate window'
        check('Wiktionary IPC commits '+row['english'],key(slot,ctrl=True,shift=shown.index(row['english'])==1)['commit']==row['english'])
    cedict_rows=[]
    for batch in ['04-cc-cedict-reviewed.tsv','05-cc-cedict-reviewed.tsv']:
        with (ROOT/'vocabulary/data/batches'/batch).open(encoding='utf-8',newline='') as stream:
            cedict_rows.extend(csv.DictReader(stream,delimiter='\t'))
    for row in cedict_rows:
        for char in pinyin_codes[row['chinese']]:result=key(char)
        items=result['frame']['candidates']['items']
        for _ in range(80):
            candidate=next((c for c in items if c['text']==row['chinese']),None)
            if candidate is not None:break
            page=send('Key',dict(session=session,event=dict(virtual_key=9,character=None,modifiers=dict(ctrl=False,shift=False,alt=False,win=False,caps=False,english_mode=False))))['KeyResult']
            next_items=page['frame']['candidates']['items']
            if [c['text'] for c in next_items]==[c['text'] for c in items]:break
            result=page;items=next_items
        sense=next((s for s in candidate['translation']['senses'] if s['text']==row['word']),None) if candidate is not None else None
        check('CC-CEDICT IPC '+row['chinese']+' exposes '+row['word'],sense is not None)
        before=[c['text'] for c in items];slot=str(items.index(candidate)+1);shown=[]
        for _ in range(len(candidate['translation']['senses'])+1):
            candidate=next(c for c in result['frame']['candidates']['items'] if c['text']==row['chinese'])
            shown=[s['text'] for s in candidate['translation']['senses'][:2]]
            if row['word'] in shown:break
            result=key(slot,ctrl=True,alt=True);items=result['frame']['candidates']['items']
            assert [c['text'] for c in items]==before,'Chinese order changed while browsing CC-CEDICT translation'
        assert row['word'] in shown,'CC-CEDICT word did not appear in the real candidate window'
        check('CC-CEDICT IPC commits '+row['word'],key(slot,ctrl=True,shift=shown.index(row['word'])==1)['commit']==row['word'])
    report=dict(passed=checks,pipe=PIPE,isolated_user_directory=str(USER),screenshot=str(screenshot),window_bounds=bounds,protocol=7)
    (ROOT/'build/desktop-tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'build/desktop-tests.txt').write_text(
        'Windows real candidate window and IPC validation: '+str(len(checks))+' checks passed.\n'
        +'\n'.join('PASS: '+name for name in checks)+'\n',
        encoding='utf-8',
    )
    pipe.close()
finally:
    process.terminate();process.wait(timeout=10)
    background.destroy()
