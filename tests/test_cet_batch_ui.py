"""真实 Android 安装包：从拼音候选展开新增四六级词并逐条输入。"""
import json

import test_android as ui
import test_speech_input as helpers
from test_exam_vocabulary_ui import settings, scroll_to


def main():
    probe = helpers.stable_probe()
    try:
        settings(['四级', '六级'])
        for pinyin, chinese, english in [('fenxi', '分析', 'analysis'), ('fazhan', '发展', 'development'),
                                         ('ziyou', '自由', 'freedom'), ('quexi', '缺席', 'absence')]:
            helpers.home()
            ui.type_pinyin(pinyin)
            ui.tap(ui.description('查看' + chinese + '的音标和释义'))
            button = scroll_to(lambda n: n.get('text') == '输入译词 ' + english, panel=True)
            ui.check('batch01 ' + chinese + ' detail exposes ' + english, button is not None)
            if english == 'analysis':
                ui.screenshot('android-0.1.11-analysis.png')
            ui.tap(button)
            ui.check('batch01 exact InputConnection commit ' + english, helpers.draft() == english)
        settings([])
        helpers.home()
        ui.type_pinyin('fenxi')
        ui.wait(lambda ns: any(n.get('description', '').startswith('分析 v. analyze') for n in ns))
        ui.check('clear goals keeps original analyze first', True)
        ui.tap(ui.exact('分析'))
        ui.check('batch01 normal candidate still commits Chinese', helpers.draft() == '分析')
        path = ui.ROOT / 'build/cet-batch01-ui-tests.json'
        path.write_text(json.dumps({'passed': ui.RESULTS}, ensure_ascii=False, indent=2), encoding='utf-8')
    finally:
        ui.adb('shell', 'am', 'force-stop', 'org.wordtrail.test')
        probe.terminate()
        probe.wait(timeout=5)


if __name__ == '__main__':
    main()
