"""Cancel local model warm-up and change dictation language with the real backend."""
import json,time
import test_android as ui
import test_speech_input as helpers

def main():
    probe=None
    try:
        ui.choose_speech_engine('本机离线');ui.adb('shell','pm','grant','org.wordtrail.ime','android.permission.RECORD_AUDIO')
        probe=helpers.stable_probe();before=helpers.home()
        ui.tap(ui.exact('中/英'));ui.description('切换中英文，当前英文')
        ui.tap(ui.description('语音输入'));ui.exact('英文 · 本机离线，录音不上网');ui.tap(ui.exact('取消'))
        time.sleep(3)
        ui.check('cancelled warm-up never opens a late recording panel',not any(n.get('description')=='停止录音并识别' for n in ui.nodes()) and ui.exact('q')['enabled'])
        ui.check('cancelled warm-up leaves the input untouched',helpers.draft()==before)
        ui.tap(ui.description('语音输入'));ui.exact('英文 · 本机离线，录音不上网');ui.exact('请说话…')
        ui.check('English mode starts the independent English recognizer',ui.description('停止录音并识别')['enabled'])
        ui.screenshot('android-local-speech-english.png');ui.tap(ui.exact('取消'))
        ui.tap(ui.exact('中/英'));ui.description('切换中英文，当前中文')
        ui.tap(ui.description('语音输入'));ui.exact('中文 · 本机离线，录音不上网');ui.exact('请说话…');time.sleep(5)
        ui.tap(ui.exact('取消'));time.sleep(1)
        ui.check('switching recognizer language restores Chinese microphone',ui.exact('Q')['enabled'])
        ui.check('cancel during preview cannot commit late text',helpers.draft()==before and not any(n.get('description')=='停止录音并识别' for n in ui.nodes()))
        (ui.ROOT/'build/local-speech-switching-tests.json').write_text(json.dumps({'passed':ui.RESULTS},ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        if probe is not None:ui.adb('shell','am','force-stop','org.wordtrail.test');probe.terminate();probe.wait(timeout=5)
        ui.adb('shell','am','force-stop','org.wordtrail.ime')

if __name__=='__main__':main()
