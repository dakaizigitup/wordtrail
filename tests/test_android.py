"""通过真实 Android UI 点击键盘，验证 JNI 和 InputConnection；只操作指定模拟器。"""
from pathlib import Path
import argparse, json, re, subprocess, time
import xml.etree.ElementTree as ET
import io
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--adb',default='D:/codex-mobile-build/sdk/platform-tools/adb.exe')
parser.add_argument('--serial',default='emulator-5556')
args = parser.parse_args()
if not args.serial.startswith('emulator-'): raise SystemExit('This automated UI test only targets an emulator.')
RESULTS = []

def adb(*arguments, timeout=30, binary=False):
    output = subprocess.check_output([args.adb,'-s',args.serial,*arguments],timeout=timeout)
    return output if binary else output.decode('utf-8',errors='replace').strip()

def nodes():
    output=adb('shell','am','instrument','-w','org.wordtrail.test/.WindowProbe')
    line=next((line for line in output.splitlines() if line.startswith('INSTRUMENTATION_RESULT: nodes=')),None)
    if line is None: raise AssertionError(output)
    return json.loads(line.split('nodes=',1)[1])

def wait(predicate, seconds=25):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        current=nodes()
        value=predicate(current)
        if value is not None and value is not False: return value
        time.sleep(.3)
    raise AssertionError('Timed out waiting for Android UI')

def exact(label):
    return wait(lambda values: next((n for n in values if n.get('text')==label),None))

def description(label):
    return wait(lambda values:next((n for n in values if n.get('description')==label),None))

def choose_speech_engine(label):
    adb('shell','am','force-stop','org.wordtrail.ime')
    adb('shell','am','start','-W','-f','0x10008000','-n','org.wordtrail.ime/.MainActivity')
    exact('词伴输入法')
    size=re.findall(r'(\d+)x(\d+)',adb('shell','wm','size'))[-1];width,height=map(int,size)
    for _ in range(6):
        choice=wait(lambda ns:next((n for n in ns if n.get('class')=='android.widget.RadioButton' and n.get('text')==label),None))
        left,top,right,bottom=map(int,re.findall(r'-?\d+',choice['bounds']))
        if 80<top<bottom<height-80:
            if not choice.get('checked'):tap(choice)
            wait(lambda ns:any(n.get('class')=='android.widget.RadioButton' and n.get('text')==label and n.get('checked') for n in ns))
            return
        adb('shell','input','swipe',str(width//2),str(height-300),str(width//2),str(height//3),'350');time.sleep(.3)
    raise AssertionError('Could not scroll to speech engine preference')

def tap(node, long=False):
    x1,y1,x2,y2=map(int,re.findall(r'\d+',node.get('bounds')))
    x,y=str((x1+x2)//2),str((y1+y2)//2)
    if long: adb('shell','input','swipe',x,y,x,y,'850')
    else: adb('shell','input','tap',x,y)

def type_pinyin(text):
    # Candidate collapse changes window height. Refresh screen coordinates after
    # each tap instead of retaining a snapshot taken during a previous resize.
    for char in text:tap(exact(char.upper()))

def check(name, condition):
    assert condition, name
    RESULTS.append(name)
    print('PASS:',name,flush=True)

def field_contains(value):
    return wait(lambda ns: next((n for n in ns if n.get('class')=='android.widget.EditText' and value in n.get('text','')),None))

def screenshot(name):
    folder=ROOT/'docs/screenshots'; folder.mkdir(parents=True,exist_ok=True)
    (folder/name).write_bytes(adb('exec-out','screencap','-p',binary=True))

def choose_theme(label,expected):
    tap(exact('◐'))
    option=wait(lambda ns:next((n for n in ns if n.get('text')==label and n.get('class')=='android.widget.Button'),None))
    tap(option)
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        screen=Image.open(io.BytesIO(adb('exec-out','screencap','-p',binary=True))).convert('RGB')
        if screen.getpixel((4,screen.height-220))==expected:break
        time.sleep(.3)
    else: raise AssertionError('Theme did not repaint the keyboard: '+label)
    check(label+' theme preserves current candidates',exact('你好') is not None)

def main():
    deadline=time.monotonic()+90
    while adb('shell','getprop','sys.boot_completed')!='1':
        if time.monotonic()>deadline: raise AssertionError('Emulator boot timed out')
        time.sleep(2)
    adb('install','-r',str(ROOT/'dist/wordtrail-0.1.23-debug.apk'),timeout=90)
    adb('install','-r',str(ROOT/'build/probe/probe.apk'))
    adb('shell','settings','put','secure','show_ime_with_hard_keyboard','1')
    adb('shell','am','force-stop','org.wordtrail.ime')
    deadline=time.monotonic()+30
    while 'org.wordtrail.ime/.WordtrailIME' not in adb('shell','ime','list','-a','-s'):
        if time.monotonic()>deadline: raise AssertionError('Installed IME was not registered')
        time.sleep(1)
    adb('shell','ime','enable','org.wordtrail.ime/.WordtrailIME')
    adb('shell','ime','set','org.wordtrail.ime/.WordtrailIME')
    adb('shell','am','start','-n','org.wordtrail.ime/.MainActivity')
    tap(exact('英语'))
    test=wait(lambda ns: next((n for n in ns if n.get('class')=='android.widget.EditText'),None))
    tap(test)
    # Force-stop/reinstall notifications can switch back to the system IME
    # asynchronously. Select our IME after the host field has acquired focus.
    adb('shell','ime','set','org.wordtrail.ime/.WordtrailIME')
    exact('EN 译词')
    exact('拼音输入');time.sleep(.6)  # Wait for the engine and first window insets/layout.
    type_pinyin('nihao')
    hello=wait(lambda ns: next((n for n in ns if 'hello' in n.get('text','') and n.get('class')=='android.widget.TextView'),None))
    check('native JNI produces hello annotation',hello is not None)
    tap(description('查看你好的音标和释义'))
    check('UK pronunciation available in details',wait(lambda ns:any(n.get('text','').startswith('英式  /') for n in ns)))
    check('US pronunciation available separately in details',wait(lambda ns:any(n.get('text','').startswith('美式  /') for n in ns)))
    screenshot('android-pronunciation.png');tap(exact('收起'))
    screenshot('android-english.png')
    choose_theme('粉紫',(244,239,247));screenshot('android-lavender.png')
    choose_theme('深色',(24,35,31));screenshot('android-night.png')
    choose_theme('青绿',(238,244,239))
    tap(exact('你好'))
    check('Chinese candidate commits via InputConnection',field_contains('你好') is not None)
    type_pinyin('nihao'); tap(exact('你好'),long=True)
    check('long press commits translation',field_contains('你好hello') is not None)
    tap(exact('EN 译词')); type_pinyin('nihao')
    japanese=wait(lambda ns: next((n for n in ns if 'こんにちは' in n.get('text','')),None))
    check('Japanese glossary switch',japanese is not None)
    screenshot('android-japanese.png')
    tap(exact('JA 译词'))
    spanish=wait(lambda ns: next((n for n in ns if 'hola' in n.get('text','')),None))
    check('Spanish glossary switch',spanish is not None)
    tap(exact('你好'))
    type_pinyin('shi'); tap(exact('›'))
    check('second candidate page renders',wait(lambda ns:any(re.search(r'2/\d+',n.get('text','')) for n in ns)))
    screenshot('android-page2.png')
    tap(exact('中/英'))
    check('mode toggle commits raw pinyin',field_contains('shi') is not None)
    tap(exact('h')); tap(exact('i'))
    check('Latin typing commits direct text',field_contains('shihi') is not None)
    tap(exact('中/英')); type_pinyin('nihaoshijie'); tap(exact('你好'))
    check('partial selection keeps remaining composition',field_contains('你好shijie') is not None)
    tap(exact('空格'))
    check('remaining composition commits to Chinese',field_contains('你好世界') is not None)
    type_pinyin('bupingdeng')
    unequal_candidate=wait(lambda ns:next((n for n in ns if n.get('text')=='不平等' and n.get('class')=='android.widget.TextView'),None))
    check('batch13 runtime pinyin overlay reaches the Android candidate window',unequal_candidate is not None)
    tap(unequal_candidate)
    check('batch13 runtime candidate commits through Android InputConnection',field_contains('不平等') is not None)
    adb('shell','am','force-stop','org.wordtrail.ime')
    adb('shell','am','start','-n','org.wordtrail.ime/.MainActivity')
    crash=adb('logcat','-d','-b','crash')
    check('no application crash', 'org.wordtrail.ime' not in crash)
    exact('词伴输入法');screenshot('android-home.png')
    report={'serial':args.serial,'android':adb('shell','getprop','ro.build.version.release'),'abi':adb('shell','getprop','ro.product.cpu.abi'),'passed':RESULTS}
    (ROOT/'build/android-ui-tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
