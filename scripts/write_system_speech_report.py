"""Report verified Android 0.1.4 checks; distinguish historical layout tests."""
from pathlib import Path
import hashlib,json,shutil

ROOT=Path(__file__).resolve().parents[1]

def main():
    speech=json.loads((ROOT/'build/speech-input-tests.json').read_text(encoding='utf-8'))
    input_checks=json.loads((ROOT/'build/android-ui-tests.json').read_text(encoding='utf-8'))
    themes=json.loads((ROOT/'build/theme-settings-tests.json').read_text(encoding='utf-8'))
    assert speech['apk']=='wordtrail-0.1.4-debug.apk'
    assert len(speech['passed'])>=34 and len(input_checks['passed'])==16 and len(themes['passed'])==5
    apk=ROOT/'dist/wordtrail-0.1.4-debug.apk'
    with apk.open('rb') as stream:sha=hashlib.file_digest(stream,'sha256').hexdigest()
    cases='\n'.join('- '+case for case in speech['passed'])
    report=f'''# 安卓 0.1.4 系统语音兼容测试

2026-10-05。本版继续使用系统服务，不接独立云 API。iOS 保持 0.1.2，Windows 保持现有 0.1.1 音标补丁。本轮仅修改安卓语音选择、失败提示及设置页。

## 本版已验证

Android 15 x86_64 隔离模拟器运行最终 APK，真实系统权限 UI、RecognitionService Binder 和 InputConnection 完成 {len(speech['passed'])} 项检查：

{cases}

关键用例包括系统默认组件指向已移除服务时，手动服务与自动单服务恢复均能识别；客户端、服务器、断开连接等错误区分具体编号，并记录实际服务；取消、重复回调和换输入框不误插入文字。

识别内容由单独的测试 APK 合成，用于检查流程，不进入生产安装包。**不验证真实麦克风录音、识别准确率，也没有证明用户 iQOO 手机和平板的故障已解决。** 真实根因需要新版错误信息或 USB 调试日志确认；微信输入法语音可用也不能单独证明其开放了系统识别接口。

语音检查分两段完成：主要场景 29 项；最后的编辑器切换场景在测试宿主第一次布局过程中发生触摸位置变化，补上等待布局和麦克风启用的条件后，用独立编辑器脚本完成另外 5 项。同一安装包 SHA 校验一致，主场景执行记录和编辑器补跑记录均保留在 evidence。未将第一次未完成的全流程宣称为一次全部通过。

![具体错误和服务](screenshots/android-speech-error-details.png)

最终 APK 同时通过 {len(input_checks['passed'])} 项中文/译词/音标输入检查和 {len(themes['passed'])} 项主题设置检查。本轮合计 {len(speech['passed'])+len(input_checks['passed'])+len(themes['passed'])} 项。0.1.3 的 52 项手机、横屏平板、竖屏平板和紧凑横屏布局记录保留为历史证据，本轮没有把它们计入新版通过数。

## 安装包

`wordtrail-0.1.4-debug.apk`，versionCode 5，{apk.stat().st_size:,} 字节；SHA-256 `{sha}`。包含 arm64-v8a / x86_64，最低 Android 8，目标 Android 15。APK v2/v3 签名及 16 KB 对齐验证通过，沿用旧签名，可覆盖安装。

权限仍仅 RECORD_AUDIO，无 INTERNET。公开服务由系统查询并按用户选择明确绑定；手动服务失效时不静默切换。用户可关闭离线优先，保留使用系统服务可能联网的说明。不保存或自行上传录音，诊断不包含输入框内容。

语音设置为非导出 Activity。失败区维持 72dp，不自动重录；允许设置、切换输入法及返回。相同取消/编辑器保护继续使用。没有调用微信输入法私有接口，切换入口只打开系统输入法选择器。

共享引擎、固定上游、词库、释义和独立音标数据没有修改。源码交付保留许可证、数据来源和完整依赖。苹果未编译、无 IPA；本轮未修改或重新测试已安装桌面程序。
'''
    (ROOT/'docs/测试报告.md').write_text(report,encoding='utf-8')
    evidence=ROOT/'docs/evidence';evidence.mkdir(exist_ok=True)
    for source,destination in [('speech-input-tests.json','android-0.1.4-speech-tests.json'),('speech-system-fix-tests.log','android-0.1.4-main-scenarios.log'),('speech-input-prefix.json','android-0.1.4-main-scenarios.json'),('speech-editor-tests.log','android-0.1.4-editor-tests.log'),('speech-editor-tests.json','android-0.1.4-editor-tests.json'),('android-ui-tests.json','android-0.1.4-input-tests.json'),('system-fix-input-tests.log','android-0.1.4-input-tests.log'),('theme-settings-tests.json','android-0.1.4-theme-tests.json'),('system-fix-theme-tests.log','android-0.1.4-theme-tests.log'),('system-fix-build.log','android-0.1.4-build.log')]:
        shutil.copy2(ROOT/'build'/source,evidence/destination)
    print(json.dumps({'speech':len(speech['passed']),'input':16,'themes':5,'sha256':sha},indent=2))

if __name__=='__main__':main()
