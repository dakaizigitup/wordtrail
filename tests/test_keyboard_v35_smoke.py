"""Final-build large-font/theme/label smoke check with real IME panels."""
import json,time,io
from PIL import Image
import test_android as ui
import test_speech_input as helpers
from test_keyboard_layout_v35 import setup,box

def main():
    probe=helpers.stable_probe()
    try:
        setup('1080x2400',420,1.5)
        ui.tap(ui.exact('◐'));ui.tap(ui.exact('深色'));ui.exact('Q')
        ui.tap(ui.exact('◐'));ui.tap(ui.exact('青绿'));ui.exact('Q');time.sleep(.4)
        screen=Image.open(io.BytesIO(ui.adb('exec-out','screencap','-p',binary=True))).convert('RGB')
        layout=box(ui.description('切换到九宫格拼音'))
        ui.check('layout selector repaints after switching themes',screen.getpixel((layout[0]+12,layout[1]+12))==(238,244,239))
        ui.type_pinyin('nihao');ui.exact('你好')
        ui.check('theme switch preserves a usable keyboard',True)
        ui.check('English tags remain available alongside candidates',any('词汇标签 ' in n['description'] for n in ui.nodes()))
        ui.screenshot('v35-large-font-final.png')
        ui.tap(ui.description('查看你好的音标和释义'));ui.description('收起音标详情')
        ui.check('complete labels and IPA remain available in detail',any('英式' in n['text'] for n in ui.nodes()))
        ui.tap(ui.description('收起音标详情'));ui.tap(ui.exact('你好'));ui.field_contains('你好')
        ui.tap(ui.description('收起键盘'));ui.wait(lambda ns:not any(n['description']=='词伴键盘' for n in ns))
        ui.check('dedicated down arrow hides the keyboard',True)
        setup('1080x2400',420,1)
        ui.type_pinyin('nihao');ui.exact('你好');ui.screenshot('v35-preview-qwerty.png')
        ui.tap(ui.description('切换到九宫格拼音'))
        for digit in '64426':ui.tap(ui.wait(lambda ns:next((n for n in ns if n['description'].startswith('九键 '+digit+' ')),None)))
        if any(n['description']=='选择第1个拼音 ni' for n in ui.nodes()):
            ui.tap(ui.description('选择第1个拼音 ni'));ui.tap(ui.description('选择第2个拼音 hao'))
        else:ui.tap(ui.description("选择读音 ni'hao"))
        ui.exact('你好');ui.screenshot('v35-preview-nine.png')
        ui.tap(ui.description('展开全部候选并隐藏键盘'));ui.exact('返回键盘');ui.screenshot('v35-preview-expanded.png')
        ui.tap(ui.exact('返回键盘'));ui.tap(ui.description('切换到全键拼音'));ui.exact('Q')
        (ui.ROOT/'build/keyboard-v35-smoke.json').write_text(json.dumps({'passed':ui.RESULTS},ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        ui.adb('shell','am','force-stop','org.wordtrail.ime');ui.adb('shell','settings','put','system','font_scale','1');ui.adb('shell','wm','size','reset');ui.adb('shell','wm','density','reset');ui.adb('shell','am','force-stop','org.wordtrail.test');probe.terminate();probe.wait(timeout=5)

if __name__=='__main__':main()
