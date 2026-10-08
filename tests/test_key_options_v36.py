"""User-visible settings and held touchscreen gestures, without app restarts."""
import json,re,shlex,time
import test_android as ui
import test_speech_input as helpers
from test_keyboard_layout_v35 import setup,box,field

def draft(ns=None):
    ns=ui.nodes() if ns is None else ns
    value=next(n['text'] for n in ns if n['class']=='android.widget.EditText')
    return '' if value=='在这里输入拼音…' else value

def preference(key,value):
    label=f'设置 {key} {value}'
    for _ in range(30):
        root=box(ui.description('词伴键盘'));ns=ui.nodes();end=root[1]-20
        target=next((n for n in ns if n['description']==label and n['class']=='android.widget.RadioButton'),None)
        if target:
            left,top,right,bottom=box(target)
            if 90<=top<bottom<end and bottom-top>45:
                ui.tap(target)
                ui.wait(lambda nodes:any(n['description']==label and n['checked'] for n in nodes))
                return
        reverse=target is not None and box(target)[1]<90
        x=(root[0]+root[2])//2
        needed=(140-box(target)[1]) if reverse else (box(target)[3]-end+30) if target else 250
        step=min(250,max(90,needed),(end-190)//2)
        ui.adb('shell','input','swipe',str(x),str(160 if reverse else end-30),str(160+step if reverse else end-30-step),'800');time.sleep(.25)
    raise AssertionError('Cannot reach '+label)

def live_settings():
    original_nodes=ui.nodes
    probe=helpers.stable_probe()
    try:
        setup('1080x2400',420)
        ui.type_pinyin('nihao');ui.exact('你好');text=draft()
        preference('keyboard_height','standard');normal=box(ui.exact('Q'))
        preference('keyboard_height','tall');ui.wait(lambda ns:box(next(n for n in ns if n['text']=='Q'))[3]-box(next(n for n in ns if n['text']=='Q'))[1]>normal[3]-normal[1])
        tall=box(ui.exact('Q'));ui.check('tall setting resizes the already-open keyboard',tall[3]-tall[1]>normal[3]-normal[1])
        ui.check('height adjustment preserves current composition',draft()==text)
        ui.screenshot('v36-settings-tall.png')
        preference('keyboard_height','compact');compact=box(ui.exact('Q'));ui.check('compact setting immediately reduces key height',compact[3]-compact[1]<normal[3]-normal[1])
        preference('keyboard_height','standard');ui.exact('Q')
        preference('keyboard_bottom_gap','small');small=box(ui.exact('Q'))
        preference('keyboard_bottom_gap','raised');ui.wait(lambda ns:box(next(n for n in ns if n['text']=='Q'))[1]<small[1])
        raised=box(ui.exact('Q'));ui.check('bottom-gap setting immediately raises the keys',small[1]-raised[1]>=50)
        ui.check('bottom-gap adjustment preserves current composition',draft()==text)
        preference('keyboard_bottom_gap','standard');ui.tap(ui.exact('你好'));ui.field_contains('你好')
        preference('keyboard_layout','nine');ui.description('九键 6 MNO')
        ui.check('home nine-key setting changes an already-open keyboard',not any(n['text']=='Q' for n in ui.nodes()))
        preference('keyboard_layout','qwerty');ui.exact('Q')
        ui.check('home setting returns from nine-key to QWERTY immediately',not any(n['description']=='九键 6 MNO' for n in ui.nodes()))
        ui.check('live layout changes retain committed text',draft()=='你好')
        ui.type_pinyin('nihao');ui.exact('你好');ui.check('typing still works after live layout and height changes',draft()=='你好nihao')
        (ui.ROOT/'build/v36-live-settings-checks.json').write_text(json.dumps({'passed':ui.RESULTS},ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        ui.adb('shell','am','force-stop','org.wordtrail.test');probe.terminate();probe.wait(timeout=5)
        ui.nodes=original_nodes

def hold(label,expected,option=None,cancel=False,shot=None,replace=0,outside=False):
    before=draft();args=['shell','am','instrument','-w','-e','hold_key',shlex.quote(label)]
    if option is not None:args+=['-e','option',shlex.quote(option)]
    if cancel:args+=['-e','cancel','true']
    if outside:args+=['-e','outside','true']
    if shot:args+=['-e','shot',shot]
    output=ui.adb(*args,'org.wordtrail.test/.WindowProbe',timeout=30)
    values={line.split('=',1)[0].split(': ',1)[1]:line.split('=',1)[1] for line in output.splitlines() if line.startswith('INSTRUMENTATION_RESULT: ') and '=' in line}
    (ui.ROOT/'build/v36-last-hold.json').write_text(json.dumps(values,ensure_ascii=False,indent=2),encoding='utf-8')
    if 'error' in values:
        (ui.ROOT/'build/v36-hold-error.json').write_text(json.dumps(values,ensure_ascii=False,indent=2),encoding='utf-8')
        raise AssertionError(values['error'])
    held=json.loads(values['held_nodes']);final=json.loads(values['nodes'])
    options=[n for n in held if n['description'].startswith('长按选项 ')]
    key=next(n for n in held if (n['description']==label or n['text']==label) and not n['description'].startswith('长按选项'))
    popup=next(n for n in held if n['description']=='按键长按选项')
    ui.check(label+' popup remains above the pressed key',box(popup)[3]<=box(key)[1]+12)
    ui.check(label+' long hold shows character choices',len(options)>=2)
    ui.check(label+' hold does not also insert the primary key',draft(held)==before)
    ui.check(label+' release commits only the selected option',draft(final)==(before[:-replace] if replace else before)+expected)
    ui.check(label+' popup closes after release/cancel',not any(n['description'].startswith('长按选项 ') for n in final))
    if shot:
        screenshot=ui.adb('exec-out','cat',values['screenshot'],binary=True)
        (ui.ROOT/'docs/screenshots'/f'{shot}.png').write_bytes(screenshot)
    return options

def held_keys():
    helpers.home();ui.tap(ui.description('切换到九宫格拼音'));ui.description('九键 6 MNO')
    opts=hold('九键 6 MNO','6',shot='v36-nine-longpress')
    ui.check('nine-key choice strip contains both cases and the digit',set(n['text'] for n in opts)=={'M','N','O','6','m','n','o'})
    hold('九键 6 MNO','M',option='M');hold('九键 6 MNO','o',option='o');hold('九键 6 MNO','',cancel=True)
    hold('九键 6 MNO','',outside=True)
    ui.check('literal letters do not change Chinese input mode',ui.description('切换中英文，当前中文') is not None)
    ui.tap(ui.description('切换到全键拼音'));ui.exact('Q')
    hold('Q','1',shot='v36-qwerty-longpress');hold('L','?',shot='v36-symbol-longpress');hold('Q','Q',option='Q')
    hold('，','；',option='；')
    ui.check('Chinese alternatives stay literal and preserve letter keys',ui.exact('Q') is not None)
    ui.tap(ui.description('切换中英文，当前中文'));ui.exact('q');hold('l','?')
    ui.tap(ui.description('切换中英文，当前英文'));ui.exact('Q')
    ui.type_pinyin('nihao');ui.exact('你好');before=draft();hold('Q','你好1',replace=5)
    ui.check('long-press finalizes pending Chinese without corrupting earlier text',draft()==before[:-5]+'你好1')

def main():
    try:
        live_settings();held_keys()
        (ui.ROOT/'build/key-options-v36.json').write_text(json.dumps({'passed':ui.RESULTS},ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception:
        ui.screenshot('v36-failure.png');(ui.ROOT/'build/v36-failure-nodes.json').write_text(json.dumps(ui.nodes(),ensure_ascii=False,indent=2),encoding='utf-8');raise
    finally:
        ui.adb('shell','am','force-stop','org.wordtrail.ime');ui.adb('shell','wm','size','reset');ui.adb('shell','wm','density','reset')

if __name__=='__main__':main()
