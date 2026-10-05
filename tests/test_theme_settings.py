"""验证设置页换肤、保存和键盘读取设置；仅操作隔离模拟器。"""
import io, json, time
from PIL import Image
import test_android as ui

def palette(expected,y):
    deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        screen=Image.open(io.BytesIO(ui.adb('exec-out','screencap','-p',binary=True))).convert('RGB')
        if screen.getpixel((4,y if y>0 else screen.height+y))==expected:return True
        time.sleep(.3)
    return False

def main():
    ui.adb('shell','am','force-stop','org.wordtrail.ime')
    ui.adb('shell','am','start','-n','org.wordtrail.ime/.MainActivity')
    ui.exact('词伴输入法')
    for name,color,suffix in [('粉紫',(244,239,247),'lavender'),('深色',(24,35,31),'night')]:
        option=ui.wait(lambda ns:next((n for n in ns if n.get('text')==name and n.get('class')=='android.widget.RadioButton'),None))
        ui.tap(option);ui.check(name+' settings repaints home',palette(color,300));ui.screenshot('android-home-'+suffix+'.png')
    ui.adb('shell','am','force-stop','org.wordtrail.ime');ui.adb('shell','am','start','-n','org.wordtrail.ime/.MainActivity')
    ui.exact('词伴输入法');ui.check('theme persists after process restart',palette((24,35,31),300))
    field=ui.wait(lambda ns:next((n for n in ns if n.get('class')=='android.widget.EditText'),None));ui.tap(field)
    ui.adb('shell','ime','set','org.wordtrail.ime/.WordtrailIME');ui.exact('◐')
    # The view appears before the asynchronously loaded engine is ready.
    ui.exact('拼音输入')
    ui.check('keyboard loads theme selected in settings',palette((24,35,31),-220))
    ui.type_pinyin('nihao');ui.exact('你好');ui.choose_theme('青绿',(238,244,239))
    ui.adb('shell','am','force-stop','org.wordtrail.ime');ui.adb('shell','am','start','-n','org.wordtrail.ime/.MainActivity');ui.exact('词伴输入法');ui.screenshot('android-home.png')
    (ui.ROOT/'build/theme-settings-tests.json').write_text(json.dumps({'passed':ui.RESULTS},ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
