"""Precise English touch bursts while the local word table produces candidates."""
import json,time
import test_android as ui

def main():
    results=[]
    for gap in (120,60,30):
        ui.adb('shell','am','force-stop','org.wordtrail.ime')
        ui.adb('shell','am','start','-W','-f','0x10008000','-n','org.wordtrail.ime/.MainActivity')
        ui.tap(ui.wait(lambda ns:next((n for n in ns if n['class']=='android.widget.EditText'),None)))
        ui.adb('shell','ime','set','org.wordtrail.ime/.WordtrailIME');ui.exact('拼音输入');ui.tap(ui.exact('中/英'));ui.exact('英文输入');time.sleep(.5)
        text='internationalization'
        output=ui.adb('shell','am','instrument','-w','-e','burst',text,'-e','gap',str(gap),'org.wordtrail.test/.WindowProbe',timeout=45)
        line=next(x for x in output.splitlines() if x.startswith('INSTRUMENTATION_RESULT: nodes='))
        ns=json.loads(line.split('nodes=',1)[1]);actual=next(n['text'] for n in ns if n['class']=='android.widget.EditText')
        elapsed=int(next(x.split('=',1)[1] for x in output.splitlines() if x.startswith('INSTRUMENTATION_RESULT: burst_ms=')))
        results.append(dict(gap_ms=gap,expected=text,actual=actual,passed=text==actual,elapsed_ms=elapsed))
        print(json.dumps(results[-1]),flush=True)
    (ui.ROOT/'build/rapid-english-tests.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    assert all(r['passed'] for r in results)

if __name__=='__main__':main()
