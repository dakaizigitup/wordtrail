"""Exercise idle theme selection, dense hh candidates and missing-service recovery."""
import json,time
import test_android as ui
from test_adaptive_layout import bounds

def main():
    original=ui.adb('shell','settings','get','secure','voice_recognition_service')
    providers={line.split('/')[0] for line in ui.adb('shell','cmd','package','query-services','--components','-a','android.speech.RecognitionService').splitlines() if '/' in line}
    try:
        ui.choose_speech_engine('系统语音')
        for package in providers:ui.adb('shell','pm','disable-user','--user','0',package)
        ui.adb('shell','settings','delete','secure','voice_recognition_service')
        ui.adb('shell','am','force-stop','org.wordtrail.ime')
        ui.adb('shell','am','start','-W','-f','0x10008000','-n','org.wordtrail.ime/.MainActivity')
        field=ui.wait(lambda ns:next((n for n in ns if n.get('class')=='android.widget.EditText'),None));ui.tap(field)
        ui.adb('shell','ime','set','org.wordtrail.ime/.WordtrailIME');ui.exact('拼音输入');time.sleep(.6)
        ui.tap(ui.description('语音输入'));ui.exact('语音设置')
        ui.check('missing service leaves input untouched',ui.field_contains('在这里输入拼音…') is not None)
        ui.tap(ui.exact('语音设置'))
        ui.exact('没有发现可调用的系统语音服务。麦克风授权或切换离线优先无法补上缺失的服务。')
        ui.check('missing service hides empty picker and assistant settings detour',not any(n.get('text') in ('选择识别服务','打开手机语音设置') for n in ui.nodes()))
        ui.screenshot('android-compact-no-speech-service.png')
        ui.tap(ui.exact('返回键盘'));ui.exact('拼音输入');time.sleep(.4)
        q=bounds(ui.exact('Q'));toolbar=bounds(ui.description('语音输入'))
        ui.check('returning from speech settings restores collapsed idle keyboard',q[1]-toolbar[3]<=14)
        ui.tap(ui.description('切换主题'));ui.tap(ui.exact('粉紫'));ui.exact('拼音输入')
        ui.tap(ui.description('切换主题'));ui.tap(ui.exact('青绿'));ui.exact('拼音输入')
        ui.check('idle theme chooser opens and returns to typing',ui.exact('Q')['enabled'])
        ui.screenshot('android-compact-phone-idle.png')
        for _ in range(3):
            active=next(n for n in ui.nodes() if n.get('text') in ('EN 译词','JA 译词','ES 译词'))
            if active['text']=='EN 译词':break
            ui.tap(active);time.sleep(.3)
        ui.exact('EN 译词')
        ui.type_pinyin('hh');ui.exact('哈哈')
        hello=ui.description('哈哈 int. haha');box=bounds(hello)
        root=bounds(ui.description('词伴键盘'))
        visible=[n for n in ui.nodes() if n.get('class')=='android.widget.LinearLayout' and n.get('description') and bounds(n)[1]==box[1] and bounds(n)[3]==box[3] and root[0]<=bounds(n)[0]<bounds(n)[2]<=root[2]]
        ui.check('hh shows five fully visible candidates',len(visible)>=5)
        ui.screenshot('android-compact-phone-hh.png')
        ui.tap(ui.description('查看哈哈的音标和释义'));ui.exact('哈哈 · 释义');ui.exact('int. haha')
        ui.check('compact arrow reveals full glossary without committing',ui.field_contains('hh') is not None)
        ui.choose_speech_engine('本机离线')
        (ui.ROOT/'build/compact-controls-tests.json').write_text(json.dumps({'passed':ui.RESULTS,'hh_visible_candidates':len(visible)},ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        for package in providers:ui.adb('shell','pm','enable',package)
        if original=='null':ui.adb('shell','settings','delete','secure','voice_recognition_service')
        else:ui.adb('shell','settings','put','secure','voice_recognition_service',original)
        ui.adb('shell','am','force-stop','org.wordtrail.ime')

if __name__=='__main__':main()
