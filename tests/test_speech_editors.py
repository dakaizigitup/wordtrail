"""Run editor safety independently after the host's first layout has settled."""
import hashlib,json,time
import test_android as ui
import test_speech_input as speech

def main():
    original=ui.adb('shell','settings','get','secure','voice_recognition_service')
    providers={line.split('/')[0] for line in ui.adb('shell','cmd','package','query-services','--components','-a','android.speech.RecognitionService').splitlines() if '/' in line and not line.startswith('org.wordtrail.speechtest/')}
    probe=None
    try:
        ui.adb('install','-r',str(ui.ROOT/'dist/wordtrail-0.1.7-debug.apk'),timeout=90)
        ui.choose_speech_engine('系统语音')
        speech.component(True);ui.adb('shell','pm','grant','org.wordtrail.speechtest','android.permission.RECORD_AUDIO');ui.adb('shell','pm','grant','org.wordtrail.ime','android.permission.RECORD_AUDIO')
        for package in providers:ui.adb('shell','pm','disable-user','--user','0',package)
        ui.adb('shell','settings','put','secure','voice_recognition_service',speech.SERVICE)
        probe=speech.stable_probe();speech.home();speech.control('late')
        ui.adb('shell','am','start','-W','-f','0x10008000','-n','org.wordtrail.speechtest/.TestEditorActivity');time.sleep(.8)
        ui.tap(ui.description('普通输入'));ui.adb('shell','ime','set','org.wordtrail.ime/.WordtrailIME')
        ui.wait(lambda ns:next((n for n in ns if n.get('description')=='语音输入' and n.get('enabled')),None));ui.exact('拼音输入')
        speech.control('late');ui.tap(ui.description('语音输入'))
        choice=ui.wait(lambda ns:next((n for n in ns if n.get('text') in ['临时识别内容','使用系统语音']),None))
        if choice['text']=='使用系统语音':ui.tap(choice)
        ui.exact('临时识别内容')
        ui.tap(ui.description('密码输入'));time.sleep(1.5)
        state=speech.control();mic=ui.description('语音输入')
        assert not mic['enabled'] and state.get('cancels',0)>=1, {'mic':mic,'service':state,'password':ui.description('密码输入')}
        ui.check('changing editors cancels speech and blocks password dictation',True)
        ui.check('late speech result never enters password editor',ui.description('密码输入').get('text','') in ['', '密码输入'])
        ui.tap(ui.description('数字输入'));ui.check('number editor disables microphone',not ui.description('语音输入')['enabled'])
        ui.tap(ui.description('普通输入'));ui.wait(lambda ns:next((n for n in ns if n.get('description')=='语音输入' and n.get('enabled')),None));ui.check('normal editor re-enables microphone',True)
        ui.check('no application crash during speech flows','org.wordtrail.ime' not in ui.adb('logcat','-d','-b','crash'))
        report={'apk':'wordtrail-0.1.7-debug.apk','passed':ui.RESULTS}
        (ui.ROOT/'build/speech-editor-tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        if probe is not None:ui.adb('shell','am','force-stop','org.wordtrail.test');probe.terminate();probe.wait(timeout=5)
        ui.adb('shell','am','force-stop','org.wordtrail.ime');ui.adb('shell','am','force-stop','org.wordtrail.speechtest');speech.component(False)
        for package in providers:ui.adb('shell','pm','enable',package)
        if original=='null':ui.adb('shell','settings','delete','secure','voice_recognition_service')
        else:ui.adb('shell','settings','put','secure','voice_recognition_service',original)

if __name__=='__main__':main()
