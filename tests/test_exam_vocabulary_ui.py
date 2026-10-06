"""Real Android settings, compact tags, prioritized commits and detail scrolling."""
import json,re,time
import test_android as ui
import test_speech_input as helpers

def bounds(node):return tuple(map(int,re.findall(r'-?\d+',node['bounds'])))
def scroll_to(predicate,panel=False):
    width,height=map(int,re.findall(r'(\d+)x(\d+)',ui.adb('shell','wm','size'))[-1])
    for _ in range(18):
        current=ui.nodes()
        if panel:
            scroll=next(n for n in current if n.get('class')=='android.widget.ScrollView' and bounds(n)[1]>height//2)
            left,top,right,bottom=bounds(scroll)
        else:left,top,right,bottom=0,120,width,height-180
        node=next((n for n in current if predicate(n) and top<=bounds(n)[1]<bounds(n)[3]<=bottom and bounds(n)[3]-bounds(n)[1]>45),None)
        if node:return node
        target=next((n for n in current if predicate(n)),None)
        upward=target is None or bounds(target)[1]>=top
        start,end=(bottom-12,top+12 if panel else height//3) if upward else (top+12 if panel else height//3,bottom-12)
        ui.adb('shell','input','swipe',str((left+right)//2),str(start),str((left+right)//2),str(end),'450');time.sleep(.8)
    raise AssertionError('Cannot scroll to requested control')

def settings(targets):
    ui.adb('shell','am','force-stop','org.wordtrail.ime')
    ui.adb('shell','am','start','-W','-f','0x10008000','-n','org.wordtrail.ime/.MainActivity')
    clear=scroll_to(lambda n:n.get('text')=='全部词汇 / 清除目标');ui.tap(clear)
    ui.wait(lambda ns:any(n.get('text')=='全部词汇 · 原译词顺序' for n in ns))
    for label in targets:
        node=scroll_to(lambda n:n.get('description')=='优先'+label+'译词')
        ui.tap(node);ui.wait(lambda ns:any(n.get('description')=='优先'+label+'译词' and n.get('checked') for n in ns))
    # A forced process stop immediately after apply() can kill its disk write.
    time.sleep(.3)

def main():
    probe=helpers.stable_probe()
    try:
        settings(['专四']);ui.screenshot('android-0.1.10-goals.png')
        helpers.home();ui.type_pinyin('bbei')
        ui.wait(lambda ns:any(n.get('description','').startswith('宝贝 n. darling') for n in ns))
        ui.check('candidate strip has no CEFR badges even with prior settings',not any('CEFR' in n.get('description','') or re.fullmatch('[ABC][12]',n.get('text','')) for n in ui.nodes()))
        badge=ui.wait(lambda ns:next((n for n in ns if n.get('description','').startswith('darling · 考试标签 ')),None))
        ui.check('manually chosen TEM4 persists and moves darling before baby',badge['description'].startswith('darling · 考试标签 专四'))
        ui.check('multiple tags belong to the displayed English word','四级' in badge['description'] and '专八' in badge['description'])
        ui.screenshot('android-0.1.10-candidates.png')
        ui.tap(ui.exact('宝贝'),long=True);ui.check('long press inserts the displayed prioritized translation',helpers.draft()=='darling')
        helpers.home();ui.type_pinyin('bbei');ui.tap(ui.description('查看宝贝的音标和释义'));ui.exact('darling · 音标')
        ui.check('expanded IPA title follows the prioritized translation',True)
        ui.check('expanded detail has no CEFR section',not any('CEFR' in n.get('text','') for n in ui.nodes()))
        second=scroll_to(lambda n:n.get('text')=='输入译词 baby',panel=True)
        ui.tap(second);ui.check('non-target original sense remains available for explicit insertion',helpers.draft()=='baby')
        helpers.home();ui.type_pinyin('bbei');ui.tap(ui.exact('宝贝'));ui.check('normal tap still commits Chinese',helpers.draft()=='宝贝')
        settings(['六级','专四']);helpers.home();ui.type_pinyin('bbei')
        ui.wait(lambda ns:any(n.get('description','').startswith('宝贝 n. baby') for n in ns))
        ui.check('multi-selection uses OR and preserves original order on ties',True)
        settings([]);helpers.home();ui.type_pinyin('bbei');ui.wait(lambda ns:any(n.get('description','').startswith('宝贝 n. baby') for n in ns))
        ui.check('clear goals restores original order',True)
        ui.tap(ui.exact('EN 译词'));ui.exact('JA 译词')
        ui.check('Japanese candidates have no English exam badges',not any(' · 考试标签 ' in n.get('description','') for n in ui.nodes()))
        ui.tap(ui.exact('JA 译词'));ui.tap(ui.exact('ES 译词'))
        (ui.ROOT/'build/exam-vocabulary-ui-tests.json').write_text(json.dumps({'passed':ui.RESULTS},ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        ui.adb('shell','am','force-stop','org.wordtrail.test');probe.terminate();probe.wait(timeout=5)

if __name__=='__main__':main()
