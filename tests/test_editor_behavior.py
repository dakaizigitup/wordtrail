"""Real editor contracts: actions, selections, graphemes and number input types."""
import json,shlex,time,re
import test_android as ui
import test_speech_input as helpers
from test_keyboard_layout_v35 import box

def launch(kind,seed='',selection=None):
    ui.adb('shell','am','force-stop','org.wordtrail.speechtest')
    args=['shell','am','start','-W','-f','0x10008000','-n','org.wordtrail.speechtest/.BehaviorEditorActivity','--es','kind',kind]
    if seed:args+=['--es','seed',shlex.quote(seed)]
    if selection:args+=['--ei','start',str(selection[0]),'--ei','end',str(selection[1])]
    ui.adb(*args);ui.adb('shell','ime','set','org.wordtrail.ime/.WordtrailIME')
    ui.description('词伴键盘');ui.description('测试输入')
    ready='私密输入 · 不学习' if kind=='password' else '数字输入' if kind in ['number','decimal','phone'] else '直接输入 · EN' if kind=='url' else '拼音输入'
    ui.exact(ready);time.sleep(.65)

def field_equals(value):return ui.wait(lambda ns:next((n for n in ns if n['description']=='测试输入' and n['text']==value),None))
def result(value):return ui.wait(lambda ns:any(n['description']=='动作记录' and n['text']==value for n in ns))

def main():
    probe=helpers.stable_probe()
    try:
        ui.adb('shell','settings','put','secure','show_ime_with_hard_keyboard','1')
        ui.adb('shell','wm','size','1080x2400');ui.adb('shell','wm','density','420')
        for kind,label,code in [('search','搜索',3),('send','发送',4),('url','前往',2),('custom','确认订单',77),('password','完成',6)]:
            launch(kind,'demo');ui.tap(ui.description(label));result('action:'+str(code));ui.check(kind+' key invokes the advertised editor action',True)
        launch('send')
        if any(n['description']=='切换到全键拼音' for n in ui.nodes()):ui.tap(ui.description('切换到全键拼音'))
        ui.type_pinyin('nihao');ui.description('上屏');ui.tap(ui.description('上屏'));result('action:none');field_equals('nihao')
        ui.check('Enter with composition does not send the message prematurely',True)
        ui.tap(ui.description('发送'));result('action:4');ui.check('next Enter sends after composition completes',True)
        launch('next','abc');ui.tap(ui.description('下一项'));result('action:5');ui.description('完成');ui.check('next action advances focus and updates the key label',True)
        for kind in ['text','no_enter']:
            launch(kind,'a');ui.tap(ui.description('回车'));field_equals('a\n');result('action:none');ui.check(kind+' field inserts a newline',True)
        launch('text','ABCDEF',(2,5));ui.tap(ui.description('删除'));field_equals('ABF');ui.check('Delete removes only selected text',True)
        launch('url','ABCDEF',(2,5));ui.tap(ui.description('删除'));field_equals('ABF');ui.check('direct Latin mode also deletes the selection correctly',True)
        for name,emoji in [('family','👨‍👩‍👧‍👦'),('skin-tone','👍🏽'),('flag','🇨🇳'),('combining-accent','e\u0301')]:
            launch('text','A'+emoji);ui.tap(ui.description('删除'));field_equals('A');ui.check('Delete removes one complete '+name+' character',True)
        launch('number');a,b,c,z=[box(ui.exact(v)) for v in ['1','4','7','0']]
        ui.check('numeric editor uses a three-column number pad',a[1]<b[1]<c[1]<z[1] and a[0]==b[0]==c[0])
        ui.check('numeric editor offers the keyboard picker instead of an unusable alphabet key',not any(n['text']=='ABC' for n in ui.nodes()) and ui.description('切换键盘')['enabled'])
        for digit in '12345':ui.tap(ui.exact(digit))
        field_equals('12345');ui.tap(ui.description('完成'));result('action:6');ui.screenshot('v40-number-pad.png')
        launch('decimal')
        for char in '-1.5':ui.tap(ui.exact(char))
        field_equals('-1.5');ui.check('decimal field receives ASCII minus and dot',True)
        launch('phone')
        for char in '+86*#':ui.tap(ui.exact(char))
        field_equals('+86*#');ui.check('phone field exposes plus, star and hash',True)
        launch('text');ui.tap(ui.exact('123'));ui.exact('1');ui.tap(ui.exact('符号'));ui.exact('@');ui.tap(ui.exact('@'));field_equals('@')
        ui.tap(ui.exact('ABC'));ui.exact('Q');ui.check('symbols and number pages return to the selected alphabet layout',True)
        ui.screenshot('v40-text-keyboard.png')
        (ui.ROOT/'build/editor-behavior-tests.json').write_text(json.dumps({'passed':ui.RESULTS,'physical_device_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception:
        ui.screenshot('v40-failure.png');(ui.ROOT/'build/v40-failure-nodes.json').write_text(json.dumps(ui.nodes(),ensure_ascii=False,indent=2),encoding='utf-8');raise
    finally:
        ui.adb('shell','am','force-stop','org.wordtrail.ime');ui.adb('shell','am','force-stop','org.wordtrail.speechtest');ui.adb('shell','wm','size','reset');ui.adb('shell','wm','density','reset');ui.adb('shell','am','force-stop','org.wordtrail.test');probe.terminate();probe.wait(timeout=5)

if __name__=='__main__':main()
