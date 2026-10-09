"""Real touches on invisible key margins, row indents, drifts and multi-touch."""
import base64,json,time
import test_android as ui
import test_speech_input as helpers
from test_keyboard_layout_v35 import setup,box

def field(text):return ui.wait(lambda ns:any(n['class']=='android.widget.EditText' and n['text']==text for n in ns))
def point(x,y):ui.adb('shell','input','tap',str(round(x)),str(round(y)))
def run_sequence(events):
    payload=base64.b64encode(json.dumps(events).encode()).decode()
    output=ui.adb('shell','am','instrument','-w','-e','touch_sequence',payload,'org.wordtrail.test/.WindowProbe')
    line=next(x for x in output.splitlines() if x.startswith('INSTRUMENTATION_RESULT: nodes='))
    return json.loads(line.split('nodes=',1)[1])
def p(i,x,y):return dict(id=i,x=x,y=y)
def e(action,points,delay=20):return dict(action=action,points=points,delay=delay)

def main():
    probe=helpers.stable_probe()
    profiles=[]
    try:
        for name,size,density in [('phone','1080x2400',420),('tablet','2560x1600',240),('landscape','1920x1080',440)]:
            setup(size,density);scale=density/160
            bounds={ch:box(ui.exact(ch)) for ch in 'QWASLZX'};draft=''
            a,s,l=bounds['A'],bounds['S'],bounds['L'];q,w,z=bounds['Q'],bounds['W'],bounds['Z']
            points=[('A left indent',a[0]-10*scale,(a[1]+a[3])/2,'a'),
                    ('L right indent',l[2]+10*scale,(l[1]+l[3])/2,'l'),
                    ('Q right margin',q[2]+scale,(q[1]+q[3])/2,'q'),
                    ('W left margin',w[0]-scale,(w[1]+w[3])/2,'w'),
                    ('A right margin',a[2]+scale,(a[1]+a[3])/2,'a'),
                    ('S left margin',s[0]-scale,(s[1]+s[3])/2,'s'),
                    ('Q lower margin',(q[0]+q[2])/2,q[3]+scale,'q'),
                    ('A upper margin',(a[0]+a[2])/2,a[1]-scale,'a'),
                    ('Z upper margin',(z[0]+z[2])/2,z[1]-scale,'z')]
            for label,x,y,ch in points:
                point(x,y);draft+=ch;field(draft);ui.check(name+' '+label+' registers once',True)
            # 微滑出键帽但仍在本键触摸区中，应完成点按。
            ui.adb('shell','input','swipe',str(a[2]-2),str((a[1]+a[3])//2),str(a[2]+round(scale)),str((a[1]+a[3])//2),'100')
            draft+='a';field(draft);ui.check(name+' short edge drift preserves the tap',True)
            ui.screenshot('v42-'+name+'-hit-areas.png');profiles.append(dict(name=name,size=size,density=density,keys=bounds))
        setup('1080x2400',420);a=box(ui.exact('A'));s=box(ui.exact('S'));q=box(ui.exact('Q'));w=box(ui.exact('W'))
        ui.adb('shell','am','force-stop','org.wordtrail.test');probe.terminate();probe.wait(timeout=5);probe=None
        # Restore one-shot snapshot for gestures injected by the separate instrumentation.
        area_checks=list(ui.RESULTS)
        import importlib;importlib.reload(ui)
        ap=p(0,a[0]-15,(a[1]+a[3])/2);sp=p(1,s[0]-2,(s[1]+s[3])/2)
        ns=run_sequence([e(0,[ap]),e(5|(1<<8),[ap,sp]),e(6,[ap,sp]),e(1,[sp])])
        assert any(n['class']=='android.widget.EditText' and n['text']=='as' for n in ns)
        ui.check('overlapping thumbs at A/S margins both register',True)
        qp=p(0,q[2]+2,(q[1]+q[3])/2);wp=p(1,w[0]-2,(w[1]+w[3])/2)
        ns=run_sequence([e(0,[qp]),e(5|(1<<8),[qp,wp]),e(6,[qp,wp]),e(1,[wp])])
        assert any(n['class']=='android.widget.EditText' and n['text']=='asqw' for n in ns)
        ui.check('neighboring key hit areas do not steal a second pointer',True)
        ns=run_sequence([e(0,[ap]),e(3,[ap])]);assert any(n['class']=='android.widget.EditText' and n['text']=='asqw' for n in ns)
        ui.check('canceled letter touch adds no character',True)
        (ui.ROOT/'build/key-hit-area-tests.json').write_text(json.dumps(dict(profiles=profiles,checks=len(area_checks)+len(ui.RESULTS),passed=area_checks+ui.RESULTS,physical_device_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        ui.adb('shell','am','force-stop','org.wordtrail.ime');ui.adb('shell','wm','size','reset');ui.adb('shell','wm','density','reset');ui.adb('shell','am','force-stop','org.wordtrail.test')
        if probe:probe.terminate();probe.wait(timeout=5)

if __name__=='__main__':main()
