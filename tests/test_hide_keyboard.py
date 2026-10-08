"""A dedicated hide button must work during composition and local recording."""
import json,time
import test_android as ui
import test_speech_input as helpers

def hide():
    ui.tap(ui.description('收起键盘'))
    ui.wait(lambda ns:not any(n.get('description')=='词伴键盘' for n in ns))

def reopen():
    ui.tap(helpers.field());ui.description('词伴键盘');ui.exact('Q');time.sleep(.3)

def main():
    probe=None
    try:
        ui.choose_speech_engine('本机离线');ui.adb('shell','pm','grant','org.wordtrail.ime','android.permission.RECORD_AUDIO')
        probe=helpers.stable_probe();helpers.home();hide()
        ui.check('dedicated down arrow hides the idle keyboard',True)
        reopen();ui.type_pinyin('nihao');ui.exact('你好');draft=helpers.draft();hide()
        ui.check('hiding preserves the current composing text',helpers.draft()==draft)
        reopen();ui.check('tapping the input reopens the keyboard',ui.description('收起键盘')['enabled'])
        ui.tap(ui.description('切换键盘'))
        ui.wait(lambda ns:any(n.get('class')=='android.widget.ListView' for n in ns) and any(n.get('text')=='词伴输入法' for n in ns) and any(n.get('class') in ('android.widget.RadioButton','android.widget.CheckedTextView') for n in ns))
        ui.check('separate globe button still opens the input-method picker',True)
        ui.adb('shell','input','keyevent','KEYCODE_BACK')
        before=helpers.home();ui.tap(ui.description('语音输入'));ui.exact('中文 · 本机离线，录音不上网');hide();time.sleep(3)
        ui.check('hiding during model warm-up prevents late microphone startup',helpers.draft()==before and not any(n.get('description')=='词伴键盘' for n in ui.nodes()))
        reopen();ui.tap(ui.description('语音输入'));ui.exact('请说话…')
        active=ui.adb('shell','cmd','appops','get','org.wordtrail.ime','RECORD_AUDIO')
        ui.check('recording has a real active microphone operation','running' in active.lower())
        ui.check('hide button stays enabled while recording replaces letter keys',ui.description('收起键盘')['enabled'] and not any(n.get('text')=='Q' for n in ui.nodes()))
        hide();time.sleep(1)
        stopped=ui.adb('shell','cmd','appops','get','org.wordtrail.ime','RECORD_AUDIO')
        ui.check('hiding stops the real microphone operation','running' not in stopped.lower())
        ui.check('hiding local recording never commits temporary text',helpers.draft()==before)
        reopen();ui.type_pinyin('nihao');ui.tap(ui.exact('你好'))
        ui.check('typing resumes normally after hiding local recording',helpers.draft()=='你好')
        (ui.ROOT/'build/hide-keyboard-tests.json').write_text(json.dumps({'passed':ui.RESULTS,'active_microphone_appops':active,'stopped_microphone_appops':stopped},ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        if probe is not None:ui.adb('shell','am','force-stop','org.wordtrail.test');probe.terminate();probe.wait(timeout=5)
        ui.adb('shell','am','force-stop','org.wordtrail.ime')

if __name__=='__main__':main()
