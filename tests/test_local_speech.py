"""Real AudioRecord permission/cancel/editor flows, with no system ASR provider."""
import json,time
import test_android as ui
import test_speech_input as helpers

def begin():
    ui.tap(ui.description('语音输入'))
    ui.exact('中文 · 本机离线，录音不上网');ui.exact('请说话…')
    ui.check('local microphone starts without a system recognition service',ui.description('停止录音并识别')['enabled'])

def main():
    original=ui.adb('shell','settings','get','secure','voice_recognition_service')
    providers={line.split('/')[0] for line in ui.adb('shell','cmd','package','query-services','--components','-a','android.speech.RecognitionService').splitlines() if '/' in line and not line.startswith('org.wordtrail.speechtest/')}
    probe=None
    try:
        ui.choose_speech_engine('本机离线')
        helpers.component(False)
        for package in providers:ui.adb('shell','pm','disable-user','--user','0',package)
        ui.adb('shell','settings','delete','secure','voice_recognition_service')
        ui.adb('shell','pm','revoke','org.wordtrail.ime','android.permission.RECORD_AUDIO')
        ui.adb('shell','pm','clear-permission-flags','org.wordtrail.ime','android.permission.RECORD_AUDIO','user-set','user-fixed')
        probe=helpers.stable_probe();before=helpers.home()
        ui.tap(ui.description('语音输入'));ui.tap(helpers.permission_button('allow'))
        ui.description('语音输入');ui.exact('拼音输入')
        ui.check('permission grant leaves recording under user control',not any(n.get('description')=='关闭语音输入' for n in ui.nodes()))
        begin();ui.screenshot('android-local-speech-listening.png');ui.tap(ui.exact('取消'));ui.exact('拼音输入')
        ui.check('cancel discards audio and leaves the input untouched',helpers.draft()==before and ui.exact('Q')['enabled'])
        begin();time.sleep(1);ui.tap(ui.description('停止录音并识别'))
        ui.wait(lambda ns:any('没有听清' in n.get('text','') and '（7）' in n['text'] for n in ns))
        ui.check('silent audio does not hallucinate committed text',helpers.draft()==before)
        ui.screenshot('android-local-speech-silence.png');ui.tap(ui.exact('返回键盘'));ui.exact('拼音输入')
        ui.check('local error returns to normal typing',ui.exact('Q')['enabled'])
        ui.type_pinyin('ni');ui.exact('你');ui.tap(ui.description('语音输入'))
        ui.check('unfinished pinyin blocks recording',helpers.draft().endswith('ni') and ui.description('语音输入')['enabled'])
        ui.adb('shell','am','start','-W','-f','0x10008000','-n','org.wordtrail.speechtest/.TestEditorActivity');time.sleep(.8)
        ui.tap(ui.description('普通输入'));ui.adb('shell','ime','set','org.wordtrail.ime/.WordtrailIME');ui.exact('拼音输入');begin()
        ui.tap(ui.description('密码输入'));time.sleep(1)
        ui.check('switching to a password cancels local recording',not ui.description('语音输入')['enabled'] and not any(n.get('description')=='停止录音并识别' for n in ui.nodes()))
        ui.check('cancelled local speech never enters the password field',ui.description('密码输入').get('text','') in ('','密码输入'))
        ui.tap(ui.description('数字输入'));ui.check('numeric editor blocks local dictation',not ui.description('语音输入')['enabled'])
        ui.tap(ui.description('普通输入'));ui.exact('拼音输入');ui.check('returning to ordinary text re-enables local microphone',ui.description('语音输入')['enabled'])
        begin()
        ui.wait(lambda ns:any('没有听清' in n.get('text','') and '（7）' in n['text'] for n in ns),seconds=40)
        ui.check('thirty-second limit stops recording automatically',ui.exact('返回键盘') is not None)
        ui.tap(ui.exact('返回键盘'))
        ui.check('no local speech application crash','org.wordtrail.ime' not in ui.adb('logcat','-d','-b','crash'))
        (ui.ROOT/'build/local-speech-ui-tests.json').write_text(json.dumps({'apk':'wordtrail-0.1.23-debug.apk','method':'Production AudioRecord on Android 15 emulator with all public system recognition providers disabled; silence only. Recognition accuracy is checked separately using real WAV samples and the packaged offline model.','passed':ui.RESULTS},ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        if probe is not None:ui.adb('shell','am','force-stop','org.wordtrail.test');probe.terminate();probe.wait(timeout=5)
        ui.adb('shell','am','force-stop','org.wordtrail.ime');ui.adb('shell','am','force-stop','org.wordtrail.speechtest')
        for package in providers:ui.adb('shell','pm','enable',package)
        if original=='null':ui.adb('shell','settings','delete','secure','voice_recognition_service')
        else:ui.adb('shell','settings','put','secure','voice_recognition_service',original)

if __name__=='__main__':main()
