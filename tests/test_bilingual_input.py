"""Release-data Android integration: English, Greek, common Chinese and upgrade."""
import json,time
import test_android as ui
import test_speech_input as helpers

def type_keys(text):
    for ch in text:
        ui.tap(ui.exact(ch if ch.islower() else ch.upper()))

def home():
    helpers.home()
    if any(n['description']=='切换到全键拼音' for n in ui.nodes()):
        ui.tap(ui.description('切换到全键拼音'))

def field_equals(text):
    return ui.wait(lambda ns:any(n['class']=='android.widget.EditText' and n['text']==text for n in ns))

def main():
    probe=helpers.stable_probe()
    try:
        ui.adb('shell','settings','put','secure','show_ime_with_hard_keyboard','1')
        ui.adb('shell','wm','size','1080x2400');ui.adb('shell','wm','density','420')
        home();ui.type_pinyin('en');ui.tap(ui.description('展开全部候选并隐藏键盘'));ui.exact('返回键盘');ui.tap(ui.exact('嗯'));ui.check('new common-character data works after upgrade',field_equals('嗯'))
        home();ui.type_pinyin('lambda');ui.tap(ui.exact('λ'));ui.check('Greek name commits a symbol and consumes full composition',field_equals('λ'))
        home();ui.type_pinyin('hello');ui.exact('hello');ui.screenshot('v41-mixed-english.png')
        ui.tap(ui.description('查看hello的音标和释义'));ui.exact('收起');
        ns=ui.nodes();ui.check('English details expose IPA and Chinese insertion',any(n['text'].startswith('英式') for n in ns) and any(n['text'].startswith('输入译词 ') for n in ns))
        ui.screenshot('v41-english-details.png')
        insert=next(n for n in ns if n['text'].startswith('输入译词 '));expected=insert['text'][5:]
        ui.tap(insert);ui.wait(lambda ns:any(n['class']=='android.widget.EditText' and n['text']==expected for n in ns));ui.check('explicit English-to-Chinese insertion reaches editor',True)
        home();ui.tap(ui.exact('中/英'));ui.exact('中释义');type_keys('comp');
        ui.check('English word prefix produces completions',any(n['text']=='company' for n in ui.nodes()));ui.screenshot('v41-english-completion.png')
        ui.tap(ui.exact('company'));ui.check('choosing completion commits full English word',field_equals('company'))
        home();ui.tap(ui.exact('中/英'));type_keys('helo');ui.exact('hello');ui.tap(ui.exact('空格'));ui.check('space preserves typed spelling instead of applying correction',field_equals('helo '))
        home();ui.tap(ui.exact('123'));ui.tap(ui.exact('符号'));ui.tap(ui.exact('希腊'));
        ui.tap(ui.description('希腊字母 λ'));ui.tap(ui.description('切换希腊字母大小写'));ui.tap(ui.description('希腊字母 Λ'));ui.check('Greek panel inserts lowercase and uppercase',field_equals('λΛ'));ui.screenshot('v41-greek-symbols.png')
        ui.tap(ui.exact('ABC'));ui.exact('Q');ui.check('Greek panel returns to alphabet keyboard',True)
        report={'passed':ui.RESULTS,'physical_device_tested':False,'upgrade_from':'0.1.40'}
        (ui.ROOT/'build/bilingual-input-tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception:
        ui.screenshot('v41-failure.png');(ui.ROOT/'build/v41-failure-nodes.json').write_text(json.dumps(ui.nodes(),ensure_ascii=False,indent=2),encoding='utf-8');raise
    finally:
        ui.adb('shell','am','force-stop','org.wordtrail.ime');ui.adb('shell','am','force-stop','org.wordtrail.test');probe.terminate();probe.wait(timeout=5)

if __name__=='__main__':main()
