"""Actual Android APK: new translations, goal priority and scrolling commits."""
import json,time
import test_android as ui
import test_speech_input as helpers
from test_exam_vocabulary_ui import settings,scroll_to

def main():
    probe=helpers.stable_probe()
    try:
        settings(['六级']);helpers.home();ui.type_pinyin('yijiaren')
        ui.wait(lambda ns:any(n.get('description','').startswith('一家人 n. household') for n in ns))
        ui.check('new CET6 household is visible as first translation',True)
        ui.screenshot('android-0.1.10-priority.png')
        ui.tap(ui.exact('一家人'),long=True)
        ui.check('long press commits actual new prioritized household',helpers.draft()=='household')
        settings([]);helpers.home();ui.type_pinyin('fangqi')
        ui.wait(lambda ns:any(n.get('description','').startswith('放弃 v. give up') for n in ns))
        ui.check('clearing goals retains original first sense',True)
        ui.tap(ui.description('查看放弃的音标和释义'))
        original=scroll_to(lambda n:n.get('text')=='输入译词 abandon',panel=True)
        ui.check('original secondary abandon remains available in details',original is not None)
        new=scroll_to(lambda n:n.get('text')=='输入译词 relinquish',panel=True)
        ui.check('new third-or-later word is reached by vertical detail scrolling',new is not None)
        ui.screenshot('android-0.1.10-expanded.png');ui.tap(new)
        ui.check('detail button inserts the exact new word after scrolling',helpers.draft()=='relinquish')
        helpers.home();ui.type_pinyin('fangqi');ui.tap(ui.exact('放弃'))
        ui.check('normal candidate tap still commits Chinese',helpers.draft()=='放弃')
        (ui.ROOT/'build/expansion-ui-tests.json').write_text(json.dumps({'passed':ui.RESULTS},ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        ui.adb('shell','am','force-stop','org.wordtrail.test');probe.terminate();probe.wait(timeout=5)

if __name__=='__main__':main()
