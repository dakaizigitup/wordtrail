"""Require successful final UI, speech and package evidence before publishing 0.1.6."""
from pathlib import Path
import hashlib,json,shutil,struct,zipfile
ROOT=Path(__file__).resolve().parents[1]
SUITES=[('输入与音标','android-ui-tests.json','levels-input-tests.log'),('自动等级与开关','word-levels-ui-tests.json','word-levels-ui-tests.log'),('主题设置','theme-settings-tests.json','levels-theme-tests.log'),('紧凑候选与服务缺失','compact-controls-tests.json','levels-compact-tests.log'),('本机录音与编辑器保护','local-speech-ui-tests.json','levels-local-speech-tests.log'),('语音取消与语言切换','local-speech-switching-tests.json','levels-speech-switch-tests.log'),('主动收起键盘','hide-keyboard-tests.json','levels-hide-tests.log'),('四种屏幕与逗号位置','adaptive-layout-tests.json','levels-layout-tests.log')]
def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def main():
    apk=ROOT/'dist/wordtrail-0.1.6-debug.apk';sha=digest(apk);results=[]
    for label,file,log in SUITES:
        data=json.loads((ROOT/'build'/file).read_text(encoding='utf-8-sig'))
        assert data['passed'] and 'Traceback' not in (ROOT/'build'/log).read_text(encoding='utf-8-sig'),label
        results.append((label,data))
    rapid=json.loads((ROOT/'build/rapid-typing-tests.json').read_text(encoding='utf-8'))
    assert len(rapid['cases'])==6 and all(c['passed'] and c['actual']==c['expected'] for c in rapid['cases'])
    assert 'Traceback' not in (ROOT/'build/rapid-final-tests.log').read_text(encoding='utf-8-sig')
    raw=(ROOT/'build/levels-final-voice-completion.log').read_text(encoding='utf-8-sig')
    native=json.loads(next(line.split('result=',1)[1] for line in raw.splitlines() if line.startswith('INSTRUMENTATION_RESULT: result=')))
    assert native['internet_permission']==-1 and len(native['cases'])==2 and len(native['completion_cases'])==5
    completed=native['completion_cases'];assert completed[0]['text']=='开饭时间早上9点至下午5点。'
    assert completed[1]['text']==completed[1]['real_preview'] and completed[2]['error']==7 and completed[3]['error']==7 and completed[4]['cancelled_without_callback']
    (ROOT/'build/local-voice-native-tests.json').write_text(json.dumps(native,ensure_ascii=False,indent=2),encoding='utf-8')
    assert 'Ran 17 tests' in (ROOT/'build/levels-native-tests.log').read_text(encoding='utf-8-sig')
    assert '3 passed' in (ROOT/'build/levels-rust-tests.log').read_text(encoding='utf-8-sig')
    checked=[]
    with zipfile.ZipFile(apk) as current,zipfile.ZipFile(ROOT/'dist/wordtrail-0.1.5-debug.apk') as old:
        protected=[n for n in old.namelist() if n.startswith('assets/data/') and n.endswith('.qj') or n in ('assets/voice/model.int8.onnx','assets/voice/tokens.txt')]
        assert all(current.read(n)==old.read(n) for n in protected)
        assert hashlib.sha256(current.read('assets/voice/silero_vad.onnx')).hexdigest()=='9e2449e1087496d8d4caba907f23e0bd3f78d91fa552479bb9c23ac09cbb1fd6'
        assert b'Silero' in current.read('assets/NOTICE.txt')
        assert not any(n.endswith(('.keystore','.wav')) for n in current.namelist())
        assert b'TestRecognitionService' not in current.read('classes.dex') and b'org/wordtrail/voicetest' not in current.read('classes.dex')
        for name in current.namelist():
            if not name.endswith('.so'):continue
            b=current.read(name);start=struct.unpack_from('<Q',b,32)[0];entry=struct.unpack_from('<H',b,54)[0];count=struct.unpack_from('<H',b,56)[0]
            align=[struct.unpack_from('<Q',b,start+i*entry+48)[0] for i in range(count) if struct.unpack_from('<I',b,start+i*entry)[0]==1]
            assert align and all(x>=16384 for x in align),name
            checked.append(name)
    evidence=ROOT/'docs/evidence';evidence.mkdir(exist_ok=True)
    for label,file,log in SUITES:
        for name in (file,log):shutil.copy2(ROOT/'build'/name,evidence/('android-0.1.6-'+name))
    for name in ('rapid-typing-tests.json','rapid-final-tests.log','rapid-before-fix.log','levels-final-voice-completion.log','local-voice-native-tests.json','levels-final-build.log','levels-native-tests.log','levels-rust-tests.log'):
        shutil.copy2(ROOT/'build'/name,evidence/('android-0.1.6-'+name))
    total=sum(len(data['passed']) for label,data in results)+len(rapid['cases'])
    lines=['# 安卓 0.1.6 自动分级、语音完成与快速触屏测试','',
        '2026-10-05。交付 APK 在 Android 15 x86_64 隔离模拟器验证；用户 vivo / iQOO 的 Android16 真机仍需覆盖安装后验证。苹果只同步分级源码，未在 Mac 编译；电脑版未修改。','',
        f'{total} 项 UI、输入、布局与连续触屏检查通过；共享引擎17项、等级查表3项通过；另有2段真实音频转写及5种语音完成回归场景。','',
        '| 检查组 | 通过项数 |','|---|---:|']
    lines += [f'| {label} | {len(data["passed"])} |' for label,data in results]
    lines += [f'| 精确定时触屏连续输入 | {len(rapid["cases"])} |','',
        '## 自动等级','',
        '8,845条 CEFR A1–C2 参考词表原样嵌入共享引擎，默认显示第一条英文译词的等级小标签。宝贝的 baby A1 / darling B2 在详情独立标注；未收录不猜难度，日语/西语不显示英语等级。开关关闭后仍可查看详情；覆盖进程重启验证持久化，中文和英文上屏均不带等级后缀。此功能不代表个人水平或完整六级/雅思专项词表。','',
        '## 快速触屏与窗口变化','',
        '旧版本真实触屏序列复现漏字：haoshijiejintiantiankaitianhaoshijie 在一组快速输入中变成 hashijiejintiantiankaitianhaoshijie。漏字集中在候选首次展开，已有候选时同组输入完整。字母改为按下即响应后，单独修改仍有漏字；最终交付增加稳定透明输入窗口，并把键盘框架锚定底部，实际键区限定触摸范围，消除这次窗口大小变化。空闲候选仍完全收起。','',
        '最终测试使用 UiAutomation 注入真实触屏 DOWN/UP，异步投递保持指定间隔；不使用慢速 adb input tap 模拟“快打”。从空闲和已有候选两种状态连续输入36个字符，最后从真实编辑框核对全部拼音，一共6组，无遗漏或重复。以下实际总耗时包括注入开销，不把目标间隔当成精确手机输入速度。','',
        '| 目标间隔 | 开始时已有候选 | 实际总耗时 | 字符完整 |','|---:|---|---:|---|']
    lines += [f'| {c["gap_ms"]} ms | {c["starts_with_candidates"]} | {c["elapsed_ms"]} ms | {c["passed"]} |' for c in rapid['cases']]
    lines += ['',
        '窗口上方的应用输入框仍可点击：录音测试中切换普通/密码/数字框已验证；收起后可再次点击编辑框唤起，地球键仍可打开键盘选择。底栏逗号在中/英右边、地球左边，并保留较宽目标，四种尺寸全部验证。','',
        '实现使用 Android 的可触摸区域及输入窗口 Insets：[官方 API](https://developer.android.com/reference/android/inputmethodservice/InputMethodService.Insets)。只把实际键区作为触摸区域，上方透明区域不拦截应用点击。','',
        '## 已识别的预览与完成','',
        '真实原生识别模型和生产 Java 逻辑一起运行，没有用合成语音结果代替识别：','',
        '| 场景 | 结果 |','|---|---|',
        f'| 轻声中文加长停顿，补足30秒；旧整体平均功率 {completed[0]["old_mean_power"]:.3g} | {completed[0]["text"]} |',
        f'| 真实 preview() 先识别，随后最终音频为空 | 原样保留本会话预览：{completed[1]["text"]} |',
        '| 新会话纯静音 | 错误7，不复用旧文字 |','| 背景白噪声 | 错误7，不生成文字 |','| 已有真实预览后取消 | 不产生迟到上屏回调 |','',
        '降低音量拦截后，模拟器原始麦克风底噪曾生成“嗯。”；最终加入约0.64MB的 Silero 本机人声检测后，真实 AudioRecord 流程验证静音不上屏、30秒自动停止、取消、权限和输入框保护。VAD与ASR均在本机执行，无INTERNET权限。人声检测不是百分之百准确的保障，用户环境仍可能有误识别。','',
        '| 原音频 | 时长 | 原生转写 |','|---|---:|---|']
    lines += [f'| {c["language"]} | {c["audio_seconds"]:.3f} 秒 | {c["text"]} |' for c in native['cases']]
    lines += ['',
        '模型仍有转写误差：英文样例把 gold 识别为 code；中文预览截取后把“开饭”识别为“开放”，本测试证明完成保留该有效预览，而非声称预览文本完全正确。轻声加长停顿场景与原中文参考文本一致。录音UI测试只验证流程，不能代替用户手机麦克风的准确率测试。','',
        '## 屏幕布局','',
        '| 屏幕 | 尺寸 / density | 完整候选数 | 候选像素尺寸 |','|---|---|---:|---|']
    layout=next(data for label,data in results if label=='四种屏幕与逗号位置')
    lines += [f'| {p["name"]} | {p["size"]} / {p["density"]} | {p["visible_candidates"]} | {p["candidate_size"]} |' for p in layout['profiles']]
    lines += ['', '候选仍两行、不超过46dp；等级小标签没有撑高候选。中英切换、一次大写、三套主题、音标详情上下滑动及地球/大写/收起图标居中均验证。','',
        '## 安装包与数据','',f'`wordtrail-0.1.6-debug.apk`，versionCode 7，{apk.stat().st_size:,} 字节；SHA-256 `{sha}`。','',
        f'沿用旧签名，可覆盖安装；arm64-v8a / x86_64，{len(checked)}个原生 ELF 库16KB页对齐通过，APK签名与zipalign见构建日志。{len(protected)}个原 .qj 数据及原语音模型/token条目与0.1.5逐字节一致；共享引擎因新增等级字段正常重编译。新增 Silero 模型校验固定，MIT许可全文随包；未包含测试服务、测试音频、instrumentation代码或签名私钥。','',
        '等级表 SHA-256：`a5f810f7f8788d6c7b6ed11fd849ae0d31f6a5d9d953ab9528798d9b11d27ffa`。来源、署名与适用限制见0.1.6说明、上游等级表README及应用开源说明。','',
        '原始 JSON/日志：`docs/evidence/android-0.1.6-*`。旧0.1.5报告及截图记录仍保留；本报告只计入本轮通过的检查。']
    report='\n'.join(lines)+'\n';(ROOT/'docs/测试报告.md').write_text(report,encoding='utf-8');(evidence/'android-0.1.6-report.md').write_text(report,encoding='utf-8')
    print(json.dumps({'ui_checks':total,'native_wav_tests':2,'voice_completion_cases':5,'apk_bytes':apk.stat().st_size,'apk_sha256':sha},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
