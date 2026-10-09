"""Exercise per-syllable filtering using actual IME touches and the host editor."""
import json,re,time,os
LABEL=os.environ.get('WORDTRAIL_TEST_LABEL','v39')
import test_android as ui
import test_speech_input as helpers
from test_keyboard_layout_v35 import setup,box,field_equals

def digit(value):return ui.description('九键 '+value+' '+{'2':'ABC','3':'DEF','4':'GHI','5':'JKL','6':'MNO','7':'PQRS','8':'TUV','9':'WXYZ'}[value])
def type_digits(value):
    for d in value:ui.tap(digit(d))
    ui.wait(lambda ns:any(n['class']=='android.widget.EditText' and n['text'].endswith(value) for n in ns))

def reading(step,value):
    tap_rail(f'选择第{step}个拼音 {value}')

def tap_rail(label):
    for _ in range(15):
        ns=ui.nodes();target=next((n for n in ns if n['description']==label),None)
        rail=next(n for n in ns if n['class']=='android.widget.ScrollView' and box(n)[1]>=box(next(n for n in ns if n['description']=='词伴键盘'))[1] and box(n)[2]-box(n)[0]<220)
        l,t,r,b=box(rail)
        if target and t<=box(target)[1]<box(target)[3]<=b:
            ui.tap(target);return
        ui.adb('shell','input','swipe',str((l+r)//2),str(b-12),str(t+25),'500');time.sleep(.2)
    raise AssertionError('Cannot reach '+label)

def check_stage(step):
    ns=ui.nodes();choices=[n for n in ns if n['description'].startswith('选择第')]
    ui.check('only syllable '+str(step)+' choices are shown',bool(choices) and all(n['description'].startswith(f'选择第{step}个拼音 ') and "'" not in n['text'] and '·' not in n['text'] for n in choices))
    return choices

def mode_setting(enabled):
    # Keep the keyboard open while scrolling its host preference page.
    for _ in range(25):
        ns=ui.nodes();root=box(next(n for n in ns if n['description']=='词伴键盘'))
        option=next((n for n in ns if n['description']=='九键拼音逐个选择' and n['class']=='android.widget.Switch'),None)
        if option and 90<box(option)[1]<box(option)[3]<root[1]-10:
            if option['checked']!=enabled:ui.tap(option)
            ui.wait(lambda ns:any(n['description']=='九键拼音逐个选择' and n['checked']==enabled for n in ns));return
        reverse=option is not None and box(option)[1]<90
        start=160 if reverse else root[1]-35;end=start+(180 if reverse else -180)
        ui.adb('shell','input','swipe',str(root[2]//2),str(start),str(end),'800');time.sleep(.2)
    raise AssertionError('Reading mode setting is not reachable')

def main():
    probe=helpers.stable_probe();profiles=[]
    try:
        for name,size,density in [('phone','1080x2400',420),('tablet','2560x1600',240)]:
            setup(size,density);ui.tap(ui.description('切换到九宫格拼音'));digit('6')
            type_digits('96968329');check_stage(1);ui.screenshot(LABEL+'-'+name+'-first.png')
            for step,syllable in enumerate(['wo','you','fa','x'],1):
                reading(step,syllable)
                if step<4:ui.wait(lambda ns:any(n['description'].startswith(f'选择第{step+1}个拼音 ') for n in ns));check_stage(step+1)
                else:ui.exact('已选好');ui.check(name+' all four selections complete without early commit',field_equals('96968329') is not None)
                ui.screenshot(LABEL+'-'+name+'-step-'+str(step)+'.png')
            ui.tap(ui.description('重选上一个拼音'));ui.description('选择第4个拼音 x');check_stage(4)
            ui.check(name+' backtracking preserves all digits',field_equals('96968329') is not None)
            tap_rail('重选全部拼音');ui.description('选择第1个拼音 wo');check_stage(1)
            ui.check(name+' reset does not delete the input',field_equals('96968329') is not None)
            reading(1,'wo');ui.description('选择第2个拼音 you')
            ui.tap(ui.description('展开全部候选并隐藏键盘'));ui.exact('返回键盘');check_stage(2);ui.screenshot(LABEL+'-'+name+'-expanded.png')
            wo=ui.exact('我');ui.tap(wo);ui.wait(lambda ns:any(n['class']=='android.widget.EditText' and n['text']=='我968329' for n in ns))
            ui.check(name+' partial Chinese commit keeps unresolved nine-key input',True)
            ui.tap(ui.exact('返回键盘'));ui.description('选择第1个拼音 you')
            ui.tap(ui.exact('重输'));field_equals('我');ui.check(name+' retype retains committed Chinese',True)
            type_digits('64426');reading(1,'ni');ui.description('选择第2个拼音 hao');ui.tap(digit('6'));ui.description('选择第2个拼音 hao')
            ui.check(name+' appending a digit preserves the confirmed first syllable',True)
            ui.tap(ui.description('删除'));ui.description('选择第2个拼音 hao');reading(2,'hao');ui.exact('已选好')
            ui.tap(ui.exact('你好'));field_equals('我你好');ui.check(name+' completed nihao commits correctly',True)
            profiles.append({'name':name,'size':size,'density':density})
        type_digits('64426');mode_setting(False);ui.description("选择读音 ni'hao");ui.check('whole-reading mode remains available',True)
        mode_setting(True);ui.description('选择第1个拼音 ni');ui.check('step mode can be enabled without clearing typed digits',field_equals('我你好64426') is not None)
        (ui.ROOT/'build/progressive-reading-tests.json').write_text(json.dumps({'profiles':profiles,'passed':ui.RESULTS},ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception:
        ui.screenshot(LABEL+'-failure.png');(ui.ROOT/('build/'+LABEL+'-failure-nodes.json')).write_text(json.dumps(ui.nodes(),ensure_ascii=False,indent=2),encoding='utf-8');raise
    finally:
        ui.adb('shell','am','force-stop','org.wordtrail.ime');ui.adb('shell','wm','size','reset');ui.adb('shell','wm','density','reset');ui.adb('shell','am','force-stop','org.wordtrail.test');probe.terminate();probe.wait(timeout=5)

if __name__=='__main__':main()
