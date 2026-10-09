"""Expanded hit area must preserve long-press defaults, slide choice and cancel."""
import json,shlex
import test_android as ui
import test_speech_input as helpers

def main():
    cases=[('center default',[], '~'),('indent default',['left_gap','15'],'~'),
           ('indent lower case',['left_gap','15','option','a'],'a'),
           ('indent upper case',['left_gap','15','option','A'],'A'),
           ('indent alternate',['left_gap','15','option','~'],'~'),
           ('indent outside cancel',['left_gap','15','outside','true'],''),
           ('indent system cancel',['left_gap','15','cancel','true'],'')]
    results=[]
    for name,extra,expected in cases:
        helpers.home()
        if any(n['description']=='切换到全键拼音' for n in ui.nodes()):ui.tap(ui.description('切换到全键拼音'))
        command=['shell','am','instrument','-w','-e','hold_key','A']
        for i in range(0,len(extra),2):command+=['-e',extra[i],shlex.quote(extra[i+1])]
        output=ui.adb(*command,'org.wordtrail.test/.WindowProbe')
        line=next((x for x in output.splitlines() if x.startswith('INSTRUMENTATION_RESULT: nodes=')),None)
        assert line,output
        ns=json.loads(line.split('nodes=',1)[1]);actual=next(n['text'] for n in ns if n['class']=='android.widget.EditText')
        if actual=='在这里输入拼音…':actual=''
        assert actual==expected,(name,expected,actual)
        results.append(dict(name=name,expected=expected,actual=actual,passed=True));print('PASS:',name,flush=True)
    (ui.ROOT/'build/key-hit-hold-tests.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
