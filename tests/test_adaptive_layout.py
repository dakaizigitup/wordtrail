"""Real input/window checks on phone, tablet landscape/portrait and a compact window."""
import io,json,re,time
from PIL import Image
import test_android as ui
import test_speech_input as helpers
import os

def bounds(node):return tuple(map(int,re.findall(r'-?\d+',node['bounds'])))
def setup(size,density):
    ui.adb('shell','am','force-stop','org.wordtrail.ime')
    ui.adb('shell','wm','size',size);ui.adb('shell','wm','density',str(density))
    time.sleep(2)
    ui.adb('shell','am','start','-W','-f','0x10008000','-n','org.wordtrail.ime/.MainActivity')
    ui.tap(ui.exact('英语'))
    field=ui.wait(lambda ns:next((n for n in ns if n.get('class')=='android.widget.EditText'),None));ui.tap(field)
    ui.adb('shell','ime','set','org.wordtrail.ime/.WordtrailIME')
    ui.description('切换中英文，当前中文');ui.exact('拼音输入');time.sleep(.6)
    # Confirm the keyboard language after launching a fresh host window.
    for _ in range(3):
        active=next(n for n in ui.nodes() if n.get('text') in ('EN 译词','JA 译词','ES 译词'))
        if active['text']=='EN 译词':break
        ui.tap(active);time.sleep(.3)
    ui.exact('EN 译词')

def check_icon_center(description):
    box=bounds(ui.description(description))
    image=Image.open(io.BytesIO(ui.adb('exec-out','screencap','-p',binary=True))).convert('RGB').crop(box)
    pixels=[(x,y) for y in range(image.height) for x in range(image.width) if image.getpixel((x,y))==(36,57,45)]
    assert pixels,description+' missing visible icon'
    x=(min(p[0] for p in pixels)+max(p[0] for p in pixels))/2
    y=(min(p[1] for p in pixels)+max(p[1] for p in pixels))/2
    ui.check(description+' icon visually centered',abs(x-(image.width-1)/2)<=3 and abs(y-(image.height-1)/2)<=3)

def candidate(text):return ui.wait(lambda ns:next((n for n in ns if n.get('description','').startswith(text+' ') and n.get('class')=='android.widget.LinearLayout'),None))

def main():
    profiles=[]
    probe=helpers.stable_probe()
    try:
        for name,size,density in [('phone','1080x2160',440),('tablet-landscape','2560x1600',240),('tablet-portrait','1600x2560',240),('compact-landscape','1920x1080',440)]:
            if os.environ.get('WORDTRAIL_TEST_PROFILE') and name!=os.environ['WORDTRAIL_TEST_PROFILE']:continue
            setup(size,density);scale=density/160
            keyboard=bounds(ui.description('词伴键盘'));mode=bounds(ui.exact('中/英'));space=bounds(ui.exact('空格'))
            q=bounds(ui.exact('Q'));p=bounds(ui.exact('P'))
            width,height=map(int,size.split('x'))
            ui.check(name+' mode switch shares bottom row with space',mode[1]==space[1] and mode[3]==space[3])
            comma=bounds(ui.exact('，'));globe=bounds(ui.description('切换键盘'))
            ui.check(name+' comma is left of globe and has the wider touch target',mode[2]<comma[0]<comma[2]<globe[0]<globe[2]<space[0] and comma[2]-comma[0]>globe[2]-globe[0])
            ui.check(name+' idle keyboard remains compact',(keyboard[3]-keyboard[1])/scale<(390 if name.startswith('tablet') else 360))
            toolbar=bounds(ui.description('语音输入'))
            ui.check(name+' idle candidates collapse completely',0<=(q[1]-toolbar[3])/scale<=5)
            ui.check(name+' keyboard width is capped and centered',(p[2]-q[0])/scale<=1000 and abs((q[0]+p[2])/2-width/2)<=3)
            check_icon_center('切换键盘');check_icon_center('大写');check_icon_center('收起键盘')
            ui.screenshot('android-'+name+'-idle.png')
            ui.type_pinyin('bbei');ui.exact('宝贝');ui.exact('必备')
            baby=bounds(candidate('宝贝'));essential=bounds(candidate('必备'))
            ui.check(name+' candidate cards have equal size and alignment',baby[2]-baby[0]==essential[2]-essential[0] and baby[1]==essential[1] and baby[3]==essential[3])
            # Accessibility includes fully clipped children with zero-width bounds.
            # Count only complete, visible cards, not every off-screen candidate.
            visible=[n for n in ui.nodes() if n.get('class')=='android.widget.LinearLayout' and n.get('description','') and n['description']!='词伴键盘' and bounds(n)[1]==baby[1] and bounds(n)[3]==baby[3] and bounds(n)[2]-bounds(n)[0]==baby[2]-baby[0] and bounds(n)[0]>=q[0]-int(4*scale) and bounds(n)[2]<=p[2]+int(4*scale)]
            ui.check(name+' shows at least five candidates at once',len(visible)>=5)
            ui.check(name+' candidate strip is at most 46dp high',(baby[3]-baby[1])/scale<=46)
            hint=bounds(ui.description('查看宝贝的音标和释义'))
            ui.check(name+' pronunciation hint stays inside its card',baby[0]<=hint[0] and hint[2]<=baby[2] and baby[1]<=hint[1] and hint[3]<=baby[3])
            ui.screenshot('android-'+name+'-candidates.png')
            x=(baby[0]+baby[2])//2;y=baby[1]+int(9*scale)
            ui.adb('shell','input','swipe',str(x),str(y),str(x),str(y+int(36*scale)),'250')
            ui.exact('baby · 音标');ui.field_contains('bbei')
            ui.check(name+' swipe expands pronunciation without committing',ui.exact('收起') is not None)
            ui.screenshot('android-'+name+'-details.png');ui.tap(ui.exact('收起'))
            ui.tap(ui.description('查看必备的音标和释义'))
            ui.exact('essential · 音标')
            us=ui.wait(lambda ns:next((n for n in ns if n.get('text','').startswith('美式  ')),None))
            ui.check(name+' multiple pronunciations remain available',us['text'].count('/')>=4)
            root=bounds(ui.description('词伴键盘'))
            scroll=ui.wait(lambda ns:next((n for n in ns if n.get('class')=='android.widget.ScrollView' and bounds(n)[1]>=root[1]),None))
            region=bounds(scroll);sx=(region[0]+region[2])//2
            ui.adb('shell','input','swipe',str(sx),str(region[3]-int(8*scale)),str(sx),str(region[1]+int(8*scale)),'250')
            ui.check(name+' pronunciation scroll preserves composition',ui.field_contains('bbei') is not None)
            ui.screenshot('android-'+name+'-variants.png');ui.tap(ui.exact('收起'))
            ui.tap(ui.exact('宝贝'));ui.field_contains('宝贝')
            ui.tap(ui.exact('中/英'));ui.description('切换中英文，当前英文')
            ui.tap(ui.exact('h'));ui.tap(ui.exact('i'));ui.field_contains('宝贝hi')
            ui.check(name+' bottom mode switch types real English',True)
            ui.tap(ui.description('大写'));ui.tap(ui.exact('H'));ui.tap(ui.exact('i'));ui.field_contains('宝贝hiHi')
            ui.check(name+' shift inserts uppercase once then returns to lowercase',True)
            ui.tap(ui.exact('中/英'));ui.description('切换中英文，当前中文');ui.type_pinyin('nihao');ui.tap(ui.exact('你好'));ui.field_contains('宝贝hiHi你好')
            ui.check(name+' bottom mode switch returns to Chinese',True)
            profiles.append(dict(name=name,size=size,density=density,idle_keyboard=keyboard,key_span=[q[0],p[2]],visible_candidates=len(visible),candidate_size=[baby[2]-baby[0],baby[3]-baby[1]]))
        (ui.ROOT/'build/adaptive-layout-tests.json').write_text(json.dumps(dict(profiles=profiles,passed=ui.RESULTS),ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception:
        ui.screenshot('adaptive-failure.png')
        (ui.ROOT/'build/adaptive-failure-nodes.json').write_text(json.dumps(ui.nodes(),ensure_ascii=False,indent=2),encoding='utf-8')
        raise
    finally:
        ui.adb('shell','am','force-stop','org.wordtrail.ime');ui.adb('shell','wm','size','reset');ui.adb('shell','wm','density','reset')
        ui.adb('shell','am','force-stop','org.wordtrail.test');probe.terminate();probe.wait(timeout=5)

if __name__=='__main__':main()
