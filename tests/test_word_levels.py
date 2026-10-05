"""Automatic CEFR display, individual senses, unknowns, persistence and unmodified commits."""
import json,re,time
import test_android as ui
import test_speech_input as helpers

def set_display(enabled):
    ui.adb('shell','am','force-stop','org.wordtrail.ime')
    ui.adb('shell','am','start','-W','-f','0x10008000','-n','org.wordtrail.ime/.MainActivity')
    width,height=map(int,re.findall(r'(\d+)x(\d+)',ui.adb('shell','wm','size'))[-1])
    for _ in range(6):
        node=ui.description('候选显示英语等级')
        left,top,right,bottom=map(int,re.findall(r'-?\d+',node['bounds']))
        if 80<top<bottom<height-80:
            if node['checked']!=enabled:ui.tap(node)
            ui.wait(lambda ns:any(n.get('description')=='候选显示英语等级' and n['checked']==enabled for n in ns));return
        ui.adb('shell','input','swipe',str(width//2),str(height-300),str(width//2),str(height//3),'350');time.sleep(.3)
    raise AssertionError('Could not scroll to word-level setting')

def badges():return [n for n in ui.nodes() if n.get('class')=='android.widget.TextView' and ' · CEFR ' in n.get('description','')]

def main():
    probe=helpers.stable_probe()
    try:
        helpers.home()
        for _ in range(3):
            current=next(n for n in ui.nodes() if n.get('text') in ('EN 译词','JA 译词','ES 译词'))
            if current['text']=='EN 译词':break
            ui.tap(current)
        ui.exact('EN 译词');ui.type_pinyin('nihao');ui.description('hello · CEFR A1')
        ui.check('English levels appear automatically without choosing a level',True)
        ui.screenshot('android-levels-candidates.png')
        ui.tap(ui.exact('你好'));ui.check('Chinese commit contains no word-level suffix',helpers.draft()=='你好')
        ui.type_pinyin('nihao');ui.tap(ui.exact('你好'),long=True);ui.check('translation commit contains no word-level suffix',helpers.draft()=='你好hello')
        helpers.home();ui.type_pinyin('bbei');ui.description('baby · CEFR A1');ui.tap(ui.description('查看宝贝的音标和释义'))
        ui.exact('baby · A1 入门');ui.exact('darling · B2 中高级')
        ui.check('multiple translations show independent reference levels',True)
        ui.wait(lambda ns:any(n.get('text','').startswith('英式  /') for n in ns));ui.check('word levels preserve pronunciation data',True)
        ui.screenshot('android-levels-details.png');ui.tap(ui.exact('收起'));ui.tap(ui.exact('宝贝'))
        helpers.home();ui.type_pinyin('xiabo');ui.tap(ui.description('查看下拨的音标和释义'));ui.exact('allocate · 未收录（不代表难度）')
        ui.check('unlisted translation is explicitly unknown rather than assigned a level',True)
        ui.tap(ui.exact('收起'));ui.tap(ui.exact('下拨'));ui.type_pinyin('nihao');ui.tap(ui.exact('EN 译词'));ui.exact('JA 译词')
        ui.check('Japanese annotations do not inherit English levels',not badges())
        ui.tap(ui.exact('JA 译词'));ui.exact('ES 译词');ui.check('Spanish annotations do not inherit English levels',not badges())
        ui.tap(ui.exact('ES 译词'));ui.exact('EN 译词');ui.description('hello · CEFR A1')
        ui.check('returning to English restores automatic levels',True)
        set_display(False);helpers.home();ui.type_pinyin('nihao');ui.exact('你好')
        ui.check('optional display switch persists across process restarts',not badges())
        ui.tap(ui.description('查看你好的音标和释义'));ui.exact('hello · A1 入门')
        ui.check('hiding compact badges keeps reference levels in details',True)
        set_display(True);helpers.home();ui.type_pinyin('nihao');ui.description('hello · CEFR A1')
        ui.check('re-enabling display restores badges',True)
        (ui.ROOT/'build/word-levels-ui-tests.json').write_text(json.dumps({'passed':ui.RESULTS},ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        ui.adb('shell','am','force-stop','org.wordtrail.test');probe.terminate();probe.wait(timeout=5)
        ui.adb('shell','am','force-stop','org.wordtrail.ime')

if __name__=='__main__':main()
