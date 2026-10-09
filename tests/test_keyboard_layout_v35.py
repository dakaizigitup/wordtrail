"""Exercise replacement panels and real editor input on isolated Android emulator."""
import json, re, time, os
LABEL=os.environ.get("WORDTRAIL_TEST_LABEL","v35")
import test_android as ui
import test_speech_input as helpers

def box(n): return tuple(map(int,re.findall(r'-?\d+',n['bounds'])))
def field(): return ui.wait(lambda ns:next((n for n in ns if n['class']=='android.widget.EditText'),None))
def field_equals(text): return ui.wait(lambda ns:next((n for n in ns if n['class']=='android.widget.EditText' and n['text']==text),None))
def candidate(text): return ui.wait(lambda ns:next((n for n in ns if n['class']=='android.widget.LinearLayout' and n['description'].startswith(text+' ')),None))
def setup(size,density,font=1):
    ui.adb('shell','am','force-stop','org.wordtrail.ime')
    ui.adb('shell','settings','put','system','font_scale',str(font))
    ui.adb('shell','wm','size',size);ui.adb('shell','wm','density',str(density));time.sleep(1)
    ui.adb('shell','am','start','-W','-f','0x10008000','-n','org.wordtrail.ime/.MainActivity')
    ui.tap(field());ui.adb('shell','ime','set','org.wordtrail.ime/.WordtrailIME')
    ui.description('语音输入');time.sleep(.6)
    if any(n['description']=='切换到全键拼音' for n in ui.nodes()):ui.tap(ui.description('切换到全键拼音'))
    ui.exact('Q')

def main():
    probe=helpers.stable_probe();results=[]
    try:
        for name,size,density,font in [('phone','1080x2400',420,1),('phone-large-font','1080x2400',420,1.5),('tablet','2560x1600',240,1),('landscape','1920x1080',440,1)]:
            setup(size,density,font);scale=density/160
            q=box(ui.exact('Q'));bottom=box(ui.description('回车'));root=box(ui.description('词伴键盘'))
            ui.check(name+' bottom breathing room',root[3]-bottom[3]>=int(10*scale))
            ui.screenshot(LABEL+'-'+name+'-idle.png')
            ui.type_pinyin('haokan');ui.exact('好看');time.sleep(.4)
            ui.check(name+' typing does not move letter keys',q==box(ui.exact('Q')))
            c=box(candidate('好看'));word=box(ui.exact('好看'));hint=box(ui.description('查看好看的音标和释义'))
            ui.check(name+' full Chinese and gloss stay inside candidate',c[1]<=word[1]<word[3]<=hint[1]<hint[3]<=c[3])
            ui.screenshot(LABEL+'-'+name+'-candidates.png')
            before=box(ui.description('词伴键盘'));ui.tap(ui.description('展开全部候选并隐藏键盘'));ui.exact('返回键盘');time.sleep(.4)
            ui.check(name+' expanded candidates replace keyboard without resize',before==box(ui.description('词伴键盘')))
            ui.check(name+' letters absent when candidates expanded',not any(n['text']=='Q' for n in ui.nodes()))
            ui.screenshot(LABEL+'-'+name+'-expanded.png');ui.adb('shell','input','keyevent','4');ui.exact('Q');ui.field_contains('haokan')
            ui.check(name+' Android back collapses candidates before hiding IME',True)
            ui.tap(ui.description('查看好看的音标和释义'));ui.description('收起音标详情');time.sleep(.3)
            ui.check(name+' details replace keys without increasing height',before==box(ui.description('词伴键盘')) and not any(n['text']=='Q' for n in ui.nodes()))
            ui.screenshot(LABEL+'-'+name+'-details.png');ui.adb('shell','input','keyevent','4');ui.exact('Q');ui.tap(ui.exact('好看'));ui.field_contains('好看')
            ui.tap(ui.description('切换到九宫格拼音'));ui.description('九键 6 MNO')
            for digit in '64426':ui.tap(ui.wait(lambda ns:next((n for n in ns if n['description'].startswith('九键 '+digit+' ')),None)))
            if any(n['description']=='选择第1个拼音 ni' for n in ui.nodes()):
                ui.tap(ui.description('选择第1个拼音 ni'));ui.tap(ui.description('选择第2个拼音 hao'))
            else:ui.tap(ui.description("选择读音 ni'hao"))
            ui.exact('你好')
            ui.screenshot(LABEL+'-'+name+'-nine.png');ui.tap(ui.description('展开全部候选并隐藏键盘'));ui.exact('返回键盘');ui.exact('你好')
            ui.screenshot(LABEL+'-'+name+'-nine-expanded.png');ui.tap(ui.exact('你好'));ui.field_contains('好看你好')
            ui.check(name+' selecting nine-key candidate restores keys',ui.description('九键 6 MNO') is not None)
            ui.tap(ui.description('九键 6 MNO'));ui.tap(ui.exact('重输'));ui.check(name+' retype preserves already committed text',field_equals('好看你好') is not None)
            ui.tap(ui.description('九键 6 MNO'));ui.tap(ui.description('删除'));ui.check(name+' nine-key delete clears only composition',field_equals('好看你好') is not None)
            ui.tap(ui.exact('123'));ui.exact('1');ui.tap(ui.exact('1'));ui.tap(ui.description('删除'));ui.check(name+' numeric keyboard has working delete',field_equals('好看你好') is not None)
            ui.tap(ui.exact('ABC'));ui.tap(ui.description('切换到全键拼音'));ui.exact('Q')
            results.append(dict(profile=name,size=size,density=density,font=font,keyboard=before,candidate=c))
        (ui.ROOT/('build/keyboard-layout-'+LABEL+'.json')).write_text(json.dumps(dict(profiles=results,passed=ui.RESULTS),ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception:
        ui.screenshot(LABEL+'-failure.png');(ui.ROOT/('build/'+LABEL+'-failure-nodes.json')).write_text(json.dumps(ui.nodes(),ensure_ascii=False,indent=2),encoding='utf-8');raise
    finally:
        ui.adb('shell','am','force-stop','org.wordtrail.ime');ui.adb('shell','settings','put','system','font_scale','1');ui.adb('shell','wm','size','reset');ui.adb('shell','wm','density','reset')
        ui.adb('shell','am','force-stop','org.wordtrail.test');probe.terminate();probe.wait(timeout=5)

if __name__=='__main__':main()
