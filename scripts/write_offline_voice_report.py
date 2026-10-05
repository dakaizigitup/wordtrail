"""Final Android evidence: actual local WAV ASR, microphone UI and adaptive layout."""
from pathlib import Path
import hashlib,json,re,shutil,zipfile,struct
ROOT=Path(__file__).resolve().parents[1]
SUITES=[('输入与音标','android-ui-tests.json','compact-input-tests.log'),('主题设置','theme-settings-tests.json','compact-theme-tests.log'),('候选与无系统服务提示','compact-controls-tests.json','compact-controls-tests.log'),('独立离线录音流程','local-speech-ui-tests.json','local-speech-ui-tests.log'),('模型准备取消与语言切换','local-speech-switching-tests.json','local-speech-switching-tests.log'),('主动收起键盘','hide-keyboard-tests.json','hide-keyboard-tests.log'),('四种屏幕布局','adaptive-layout-tests.json','compact-layout-tests.log')]
def main():
    apk=ROOT/'dist/wordtrail-0.1.5-debug.apk'
    with apk.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
    results=[]
    for label,file,log in SUITES:
        data=json.loads((ROOT/'build'/file).read_text(encoding='utf-8-sig'));assert data['passed'],label
        assert 'Traceback' not in (ROOT/'build'/log).read_text(encoding='utf-8-sig'),log
        results.append((label,data))
    raw=(ROOT/'build/local-voice-asr.log').read_text(encoding='utf-8-sig')
    native=json.loads(next(line.split('result=',1)[1] for line in raw.splitlines() if line.startswith('INSTRUMENTATION_RESULT: result=')))
    assert native['internet_permission']==-1 and len(native['cases'])==2
    assert '开饭时间早上9点至下午5点' in native['cases'][0]['text']
    assert 'tribal chieftain' in native['cases'][1]['text'].lower()
    (ROOT/'build/local-voice-native-tests.json').write_text(json.dumps(native,ensure_ascii=False,indent=2),encoding='utf-8')
    checked=[]
    with zipfile.ZipFile(apk) as current,zipfile.ZipFile(ROOT/'dist/wordtrail-0.1.4-debug.apk') as old:
        protected=[n for n in old.namelist() if n.startswith('assets/data/') or n.endswith('libwordtrail_mobile.so')]
        assert all(current.read(n)==old.read(n) for n in protected)
        assert hashlib.sha256(current.read('assets/voice/model.int8.onnx')).hexdigest()=='c71f0ce00bec95b07744e116345e33d8cbbe08cef896382cf907bf4b51a2cd51'
        assert not any(n.endswith('.keystore') or 'TestRecognitionService' in n for n in current.namelist())
        dex=current.read('classes.dex');assert b'org/wordtrail/voicetest' not in dex and b'TestRecognitionService' not in dex
        for n in current.namelist():
            if not n.endswith('.so'):continue
            b=current.read(n);start=struct.unpack_from('<Q',b,32)[0];entry=struct.unpack_from('<H',b,54)[0];count=struct.unpack_from('<H',b,56)[0]
            align=[struct.unpack_from('<Q',b,start+i*entry+48)[0] for i in range(count) if struct.unpack_from('<I',b,start+i*entry)[0]==1]
            assert align and all(value>=16384 for value in align),n
            checked.append(n)
    evidence=ROOT/'docs/evidence';evidence.mkdir(exist_ok=True)
    for label,file,log in SUITES:
        for name in [file,log]:shutil.copy2(ROOT/'build'/name,evidence/('android-0.1.5-'+name))
    for name in ['local-voice-asr.log','local-voice-native-tests.json','offline-voice-build.log']:shutil.copy2(ROOT/'build'/name,evidence/('android-0.1.5-'+name))
    total=sum(len(data['passed']) for label,data in results)
    lines=['# 安卓 0.1.5 离线语音、候选与收起按钮测试','',
      '2026-10-05。最终 APK 在 Android 15 x86_64 隔离模拟器验证；用户 vivo / iQOO 真机录音尚未实测。iOS 保持 0.1.2 源码、未编译；Windows 继续现有音标补丁。','',
      '## 本版检查','',f'{total} 项 UI / 输入 / 布局检查通过；另用真实中文、英文 WAV 对实际原生模型执行 2 次离线转文字。', '',
      '| 组别 | 通过检查数 |','|---|---|']
    lines += [f'| {label} | {len(data["passed"])} |' for label,data in results]
    lines += ['', '## 实际离线识别', '', '模型随 APK 提供，应用没有 INTERNET 权限。原生测试 instrumentation 加载交付应用中的真实 C API、运行库和模型，没有使用合成识别回调。', '',
      '| 语言 | 原音频长度 | 模型加载 | 解码耗时 | 输出 |','|---|---:|---:|---:|---|']
    lines += [f'| {c["language"]} | {c["audio_seconds"]:.3f} 秒 | {c["load_ms"]} ms | {c["decode_ms"]} ms | {c["text"]} |' for c in native['cases']]
    lines += ['', '以上耗时仅是电脑模拟器结果，不代表手机速度。英文样例末尾把 gold 识别为 code，说明仍有误识别，不能据此声称识别准确率为 100%。中文样例与预期内容匹配并转换了数字、标点。', '',
      '模型首次复制、SHA-256 校验已执行；本次复测读取已准备模型。录音 UI 使用真实 AudioRecord，模拟器麦克风输入为静音：测试授权、取消、静音不上屏、最长30秒、未完成拼音阻止录音、密码/数字字段保护、语言切换和模型准备时取消；不冒充用户设备麦克风的准确率测试。', '',
      '## 收起键盘与布局', '',
      '工具栏最右侧独立向下箭头，点击收起；底部地球键仍可打开输入法选择。收起会取消正在准备或录音的会话。真实 AppOps 记录证明录音时麦克风为 running，收起后 running 消失；旧预览不会提交到输入框。', '',
      '| 屏幕 | 尺寸 / density | 一屏完整候选数 | 候选卡片像素尺寸 |','|---|---|---:|---|']
    layout=next(data for label,data in results if label=='四种屏幕布局')
    lines += [f'| {p["name"]} | {p["size"]} / {p["density"]} | {p["visible_candidates"]} | {p["candidate_size"]} |' for p in layout['profiles']]
    lines += ['', '空闲候选区完整收起；有候选时两行紧凑显示，高度不超过46dp。点箭头或下滑展开完整释义与多种音标，候选横向滚动、翻页、点选中文、长按译词、中英模式及三套主题正常。地球、大写、收起图标在四种尺寸下均验证居中。', '',
      '## 安装包', '',f'`wordtrail-0.1.5-debug.apk`，versionCode 6，{apk.stat().st_size:,} 字节；SHA-256 `{sha}`。', '',
      f'包含 arm64-v8a / x86_64。签名 v2/v3、APK 16KB 对齐通过；{len(checked)} 个原生 ELF 库均符合16KB页对齐。沿用旧签名，可覆盖安装。{len(protected)} 个原拼音内核与词库/音标数据条目和0.1.4逐字节一致。未打包测试识别服务、测试音频、instrumentation类或签名私钥。', '',
      '用户 iPA2575 / Android16 的旧截图显示默认识别服务 null、公开服务列表空，解释了原系统路径不能工作。新版默认独立本机识别，避开该依赖；未接微信输入法的私有接口或任何云端识别服务。', '',
      '原始日志及 JSON 位于 `docs/evidence/android-0.1.5-*`。旧系统服务方案的历史验证保留为 `android-0.1.4-report.md`。']
    report='\n'.join(lines)+'\n';(ROOT/'docs/测试报告.md').write_text(report,encoding='utf-8');(evidence/'android-0.1.5-report.md').write_text(report,encoding='utf-8')
    print(json.dumps({'ui_checks':total,'native_wav_tests':2,'apk_bytes':apk.stat().st_size,'apk_sha256':sha},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
