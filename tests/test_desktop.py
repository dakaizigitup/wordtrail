"""Exercise the real Windows server over an isolated pipe and capture its candidate window."""
from pathlib import Path
import ctypes, ctypes.wintypes as W, json, os, shutil, struct, subprocess, time
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
    def key(char,ctrl=False):
        return send('Key',dict(session=session,event=dict(virtual_key=ord(char.upper()),character=char,modifiers=dict(ctrl=ctrl,shift=False,alt=False,win=False,caps=False,english_mode=False))))['KeyResult']
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
    screenshot=ROOT/'docs/screenshots/desktop-ipa.png'
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
    if (box:=window()):ImageGrab.grab(bbox=box).save(ROOT/'docs/screenshots/desktop-0.1.2-vocabulary.png')
    result=key(str(updated.index(baby)+1),ctrl=True)
    check('Ctrl digit inserts prioritized translation matching displayed frame',result['commit']=='darling')
    vocabulary.write_text('{"targets":[]}',encoding='utf-8')
    report=dict(passed=checks,pipe=PIPE,isolated_user_directory=str(USER),screenshot=str(screenshot),window_bounds=bounds,protocol=7)
    (ROOT/'build/desktop-tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    pipe.close()
finally:
    process.terminate();process.wait(timeout=10)
    background.destroy()
