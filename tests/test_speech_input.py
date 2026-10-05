"""Real IME/permission/binder tests using a separate synthetic RecognitionService.

This verifies wiring and editor safety, not recognition accuracy from actual audio.
Only modifies the designated isolated emulator and restores recognition settings.
"""
import json,re,time,subprocess,threading
import test_android as ui

SERVICE='org.wordtrail.speechtest/.TestRecognitionService'

def component(enabled):ui.adb('shell','am','broadcast','--include-stopped-packages','-n','org.wordtrail.speechtest/.TestControl','--ez','service_enabled','true' if enabled else 'false')

def stable_probe():
    process=subprocess.Popen([ui.args.adb,'-s',ui.args.serial,'shell','am','instrument','-w','-e','stream','true','org.wordtrail.test/.WindowProbe'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
    condition=threading.Condition();latest=[0,[]]
    def read():
        for line in process.stdout:
            if line.startswith('INSTRUMENTATION_STATUS: nodes='):
                with condition:latest[0]+=1;latest[1]=json.loads(line.split('nodes=',1)[1]);condition.notify_all()
    threading.Thread(target=read,daemon=True).start()
    def snapshot():
        with condition:
            version=latest[0]
            if not condition.wait_for(lambda:latest[0]>version and bool(latest[1]),timeout=8):raise AssertionError('Stable window probe stopped')
            return latest[1]
    ui.nodes=snapshot
    return process

def control(scenario=None):
    values=['shell','am','broadcast','-n','org.wordtrail.speechtest/.TestControl']
    if scenario is not None:values+=['--es','scenario',scenario]
    output=ui.adb(*values)
    match=re.search(r'data="(.*)"',output)
    if not match:raise AssertionError(output)
    return json.loads(match.group(1))

def field():return ui.wait(lambda ns:next((n for n in ns if n.get('class')=='android.widget.EditText'),None))
def draft():
    value=field().get('text','')
    # Accessibility exposes an empty EditText's hint as text on this emulator.
    return '' if value=='在这里输入拼音…' else value

def home():
    ui.adb('shell','am','force-stop','org.wordtrail.ime')
    ui.adb('shell','am','start','-W','-f','0x10008000','-n','org.wordtrail.ime/.MainActivity')
    # Force-stopping the current IME can asynchronously select the system IME.
    # Re-select our test target after focus; never test another keyboard's UI.
    for attempt in range(3):
        ui.tap(field());ui.adb('shell','ime','set','org.wordtrail.ime/.WordtrailIME')
        try:
            ui.wait(lambda ns:any(n.get('description')=='语音输入' for n in ns),seconds=5)
            ui.exact('拼音输入');break
        except AssertionError:
            if attempt==2:raise
    return draft()

def begin(scenario='success',confirm=False):
    control(scenario);ui.tap(ui.description('语音输入'))
    if confirm:
        ui.tap(ui.exact('使用系统语音'))
    ui.exact('临时识别内容')

def permission_button(which):
    choices={'deny':["don't allow","don’t allow",'不允许','deny'], 'allow':['while using the app','使用应用时','允许使用','only this time','仅限这一次']}
    predicate=lambda ns:next((n for n in ns if n.get('class')=='android.widget.Button' and any(label in n.get('text','').lower() for label in choices[which])),None)
    ui.wait(predicate);time.sleep(.8)  # Android ignores very early taps on permission dialogs.
    return ui.wait(predicate)

def check_restored():return ui.description('语音输入') is not None and ui.exact('Q').get('enabled')

def main():
    original=ui.adb('shell','settings','get','secure','voice_recognition_service')
    # Only these emulator packages are touched; never the user's phone.
    providers={line.split('/')[0] for line in ui.adb('shell','cmd','package','query-services','--components','-a','android.speech.RecognitionService').splitlines() if '/' in line and not line.startswith('org.wordtrail.speechtest/')}
    probe=None
    try:
        ui.adb('install','-r',str(ui.ROOT/'dist/wordtrail-0.1.7-debug.apk'),timeout=90)
        ui.adb('install','-r',str(ui.ROOT/'build/probe/probe.apk'))
        ui.adb('install','-r',str(ui.ROOT/'build/speech-test/speech-test.apk'))
        ui.choose_speech_engine('系统语音')
        probe=stable_probe()
        ui.adb('shell','am','force-stop','com.google.android.permissioncontroller')
        ui.adb('shell','pm','clear-permission-flags','org.wordtrail.ime','android.permission.RECORD_AUDIO','user-set','user-fixed')
        control('success')
        ui.adb('shell','pm','grant','org.wordtrail.speechtest','android.permission.RECORD_AUDIO')
        ui.adb('shell','settings','put','secure','show_ime_with_hard_keyboard','1')
        ui.adb('shell','ime','enable','org.wordtrail.ime/.WordtrailIME')
        for package in providers:ui.adb('shell','pm','disable-user','--user','0',package)
        component(False)
        ui.adb('shell','settings','delete','secure','voice_recognition_service')
        before=home();ui.tap(ui.description('语音输入'))
        ui.exact('语音设置');ui.screenshot('android-speech-unavailable.png')
        ui.check('missing recognition service explains setup and preserves input',draft()==before)
        ui.tap(ui.exact('返回键盘'));ui.check('missing service returns to normal typing',check_restored())

        component(True);ui.adb('shell','settings','put','secure','voice_recognition_service',SERVICE)
        ui.adb('shell','pm','revoke','org.wordtrail.ime','android.permission.RECORD_AUDIO')
        before=home();ui.tap(ui.description('语音输入'))
        ui.screenshot('android-speech-permission.png');ui.tap(permission_button('deny'));ui.exact('返回键盘')
        ui.check('denied microphone permission does not start recognition',control().get('starts',0)==0)
        ui.tap(ui.exact('返回键盘'));ui.tap(field());ui.description('语音输入');ui.check('permission denial leaves typing available',check_restored())
        ui.tap(ui.description('语音输入'));ui.tap(permission_button('allow'));ui.tap(field());ui.description('语音输入')
        ui.check('permission grant does not automatically record',control().get('starts',0)==0)

        # Exercise first-use consent even when rerunning after a prior test.
        ui.adb('shell','input','keyevent','KEYCODE_BACK')
        time.sleep(.6)
        for _ in range(5):
            option=ui.wait(lambda ns:next((n for n in ns if n.get('class')=='android.widget.Switch'),None))
            box=list(map(int,re.findall(r'\d+',option['bounds'])))
            if box[2]>box[0] and box[3]>box[1] and 80<box[1] and box[3]<2050:break
            ui.adb('shell','input','swipe','500','1700','500','700','350');time.sleep(.5)
        else:raise AssertionError('Voice setting did not scroll into view')
        if option['checked']:
            ui.tap(option)
            ui.wait(lambda ns:any(n.get('class')=='android.widget.Switch' and not n.get('checked') for n in ns))
        before=home()
        control('success');ui.tap(ui.description('语音输入'));ui.exact('使用系统语音');ui.screenshot('android-speech-confirm.png')
        ui.check('system recognition warns before recording',control().get('starts',0)==0)
        ui.tap(ui.exact('使用系统语音'));ui.exact('临时识别内容');ui.screenshot('android-speech-listening.png')
        ui.check('partial transcript is previewed without being inserted',draft()==before)
        info=control();ui.check('Chinese speech uses zh-CN and allows system engine fallback',info['locale']=='zh-CN' and not info['prefer_offline'])
        ui.tap(ui.exact('完成'));ui.field_contains('你好，这是语音输入。')
        ui.check('finish stops recognizer and commits final transcript',control().get('stops')==1 and check_restored())
        ui.screenshot('android-speech-result.png')

        before=home();ui.tap(ui.exact('中/英'));begin('double');ui.tap(ui.exact('完成'));ui.field_contains('Hello from voice input.')
        time.sleep(1);ui.check('English locale and duplicate results commit only once',control()['locale']=='en-US' and draft().count('Hello from voice input.')==1)

        before=home();begin('late');ui.tap(ui.exact('取消'));time.sleep(1.5)
        after=draft();canceled=control();restored=check_restored()
        assert after==before and canceled.get('cancels',0)>=1 and restored, {'before':before,'after':after,'provider':canceled,'restored':restored}
        ui.check('cancel discards partial and late final results',True)

        before=home();begin('late');ui.adb('shell','input','keyevent','KEYCODE_BACK');time.sleep(1.5)
        ui.check('hiding keyboard cancels recording without inserting late result',draft()==before and control().get('cancels',0)>=1)
        ui.tap(field());ui.description('语音输入')

        for scenario,code in [('network',2),('no-match',7),('language',13),('server',4),('client',5),('disconnected',11)]:
            before=home();control(scenario);ui.tap(ui.description('语音输入'))
            error=ui.wait(lambda ns:next((n for n in ns if '（'+str(code)+'）' in n.get('text','')),None))
            ui.check(scenario+' error exposes service and exact error code', 'org.wordtrail.speechtest' in error['text'])
            if scenario=='client':
                ui.screenshot('android-speech-error-details.png');ui.tap(ui.exact('语音设置'));ui.exact('语音输入设置')
                ui.check('settings retain actual service and client error without input text',ui.wait(lambda ns:next((n for n in ns if '上次错误：' in n.get('text','') and '（5）' in n.get('text','') and SERVICE in n.get('text','')),None)) is not None)
                ui.tap(ui.exact('选择识别服务'));ui.tap(ui.wait(lambda ns:next((n for n in ns if '\norg.wordtrail.speechtest' in n.get('text','') and 'Wordtrail' in n.get('text','')),None)))
                ui.wait(lambda ns:not any(n.get('class')=='android.widget.CheckedTextView' for n in ns))
                ui.tap(ui.exact('返回键盘'));ui.tap(field());ui.description('语音输入')
            else:ui.tap(ui.exact('返回键盘'))
            ui.check(scenario+' failure preserves input and restores keyboard',draft()==before and check_restored())

        ui.adb('shell','settings','put','secure','voice_recognition_service','removed.recognizer/.StaleService')
        before=home();begin();ui.tap(ui.exact('完成'));ui.field_contains('你好，这是语音输入。')
        ui.check('explicit provider works with stale system default',draft()==before+'你好，这是语音输入。')
        # Return to automatic selection, then prove sole-provider recovery too.
        control('client');ui.tap(ui.description('语音输入'));ui.tap(ui.exact('语音设置'));ui.tap(ui.exact('选择识别服务'))
        ui.tap(ui.exact('跟随系统（默认失效且只有一个服务时自动选择）'));ui.wait(lambda ns:not any(n.get('class')=='android.widget.CheckedTextView' for n in ns));ui.tap(ui.exact('返回键盘'));ui.tap(field());ui.description('语音输入')
        before=home();begin();ui.tap(ui.exact('完成'));ui.field_contains('你好，这是语音输入。')
        ui.check('single available provider recovers stale default automatically',draft()==before+'你好，这是语音输入。')
        ui.adb('shell','settings','put','secure','voice_recognition_service',SERVICE)

        before=home();begin('timeout');ui.tap(ui.exact('完成'));ui.exact('正在识别…')
        ui.wait(lambda ns:next((n for n in ns if '（1）' in n.get('text','')),None),seconds=15);ui.tap(ui.exact('返回键盘'))
        ui.check('missing final result times out and preserves input',draft()==before and check_restored())

        before=home();ui.type_pinyin('nihao');ui.exact('你好');control('success');ui.tap(ui.description('语音输入'));time.sleep(.6)
        ui.check('unfinished pinyin is preserved and not replaced by dictation',control().get('starts',0)==0 and ui.field_contains('nihao') is not None and ui.exact('你好') is not None)
        ui.tap(ui.exact('你好'));ui.field_contains('你好')

        control('late');before=home();ui.adb('shell','am','start','-W','-f','0x10008000','-n','org.wordtrail.speechtest/.TestEditorActivity');time.sleep(.8)
        ui.tap(ui.description('普通输入'));ui.adb('shell','ime','set','org.wordtrail.ime/.WordtrailIME')
        ui.wait(lambda ns:next((n for n in ns if n.get('description')=='语音输入' and n.get('enabled')),None));ui.exact('拼音输入');begin('late')
        ui.tap(ui.description('密码输入'));time.sleep(1.5)
        ui.check('changing editors cancels speech and blocks password dictation',not ui.description('语音输入')['enabled'] and control().get('cancels',0)>=1)
        password=ui.description('密码输入');ui.check('late speech result never enters password editor',password.get('text','') in ['', '密码输入'])
        ui.tap(ui.description('数字输入'));ui.check('number editor disables microphone',not ui.description('语音输入')['enabled'])
        ui.tap(ui.description('普通输入'));ui.check('normal editor re-enables microphone',ui.description('语音输入')['enabled'])

        ui.check('no application crash during speech flows','org.wordtrail.ime' not in ui.adb('logcat','-d','-b','crash'))
        report={'apk':'wordtrail-0.1.7-debug.apk','serial':ui.args.serial,'method':'Real Android permission UI, RecognitionService binder and InputConnection with synthetic callbacks; no actual audio accuracy test.','passed':ui.RESULTS}
        (ui.ROOT/'build/speech-input-tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
    except Exception:
        ui.screenshot('speech-failure.png')
        (ui.ROOT/'build/speech-failure-nodes.json').write_text(json.dumps(ui.nodes(),ensure_ascii=False,indent=2),encoding='utf-8')
        raise
    finally:
        if probe is not None:
            ui.adb('shell','am','force-stop','org.wordtrail.test');probe.terminate();probe.wait(timeout=5)
        ui.adb('shell','am','force-stop','org.wordtrail.ime');ui.adb('shell','am','force-stop','org.wordtrail.speechtest')
        component(False)
        for package in providers:ui.adb('shell','pm','enable',package)
        if original=='null':ui.adb('shell','settings','delete','secure','voice_recognition_service')
        else:ui.adb('shell','settings','put','secure','voice_recognition_service',original)

if __name__=='__main__':main()
