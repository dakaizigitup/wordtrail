"""Actual touchscreen bursts, including candidate expansion, no adb tap throttling."""
import json,time
import test_android as ui

def main():
    ui.adb('install','-r',str(ui.ROOT/'build/probe/probe.apk'))
    results=[]
    for gap in (120,60,30):
        for prefix in ('','ni'):
            ui.adb('shell','am','force-stop','org.wordtrail.ime')
            ui.adb('shell','am','start','-W','-n','org.wordtrail.ime/.MainActivity')
            ui.tap(ui.wait(lambda ns:next((n for n in ns if n.get('class')=='android.widget.EditText'),None)))
            ui.adb('shell','ime','set','org.wordtrail.ime/.WordtrailIME');ui.exact('拼音输入');time.sleep(.5)
            if prefix:ui.type_pinyin(prefix);ui.field_contains(prefix)
            text='haoshijiejintiantiankaitian'+ 'haoshijie'
            output=ui.adb('shell','am','instrument','-w','-e','burst',text,'-e','gap',str(gap),'org.wordtrail.test/.WindowProbe',timeout=45)
            line=next((x for x in output.splitlines() if x.startswith('INSTRUMENTATION_RESULT: nodes=')),None)
            if line is None:raise AssertionError(output)
            nodes=json.loads(line.split('nodes=',1)[1]);actual=next(n['text'] for n in nodes if n['class']=='android.widget.EditText')
            elapsed=next(x.split('=',1)[1] for x in output.splitlines() if x.startswith('INSTRUMENTATION_RESULT: burst_ms='))
            item={'gap_ms':gap,'expected':prefix+text,'actual':actual,'elapsed_ms':int(elapsed),'passed':actual==prefix+text,'starts_with_candidates':bool(prefix)}
            results.append(item);print(json.dumps(item,ensure_ascii=False),flush=True)
    (ui.ROOT/'build/rapid-typing-tests.json').write_text(json.dumps({'method':'Real injected touchscreen DOWN/UP with precise interval; UI composition checked after native queue drains.','cases':results},ensure_ascii=False,indent=2),encoding='utf-8')
    if not all(x['passed'] for x in results):raise AssertionError('Rapid touch input dropped characters; see recorded cases')

if __name__=='__main__':main()
