"""Write the 0.1.2 delivery report from completed Android checks."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def main():
    layout=json.loads((ROOT/'build/adaptive-layout-tests.json').read_text(encoding='utf-8'))
    ui=json.loads((ROOT/'build/android-ui-tests.json').read_text(encoding='utf-8'))
    theme=json.loads((ROOT/'build/theme-settings-tests.json').read_text(encoding='utf-8'))
    assert len(layout['profiles'])==4 and len(layout['passed'])>=44
    apk=ROOT/'dist/wordtrail-0.1.2-debug.apk'
    with apk.open('rb') as stream:sha=hashlib.file_digest(stream,'sha256').hexdigest()
    rows='\n'.join(f"| {p['name']} | {p['size']} | {p['density']} dpi |" for p in layout['profiles'])
    report=f'''# 词伴 0.1.2 测试报告

日期：2026-10-05。本次修改移动界面，Windows 音标补丁仍为已安装的 0.1.1。

## 自适应布局与操作

Android 15 x86_64 模拟器安装真实 APK，使用 wm 设置以下屏幕尺寸与密度，以实际触摸键盘验证 InputConnection 和原生引擎；测试后恢复模拟器默认配置。

| 配置 | 像素 | 密度 |
|---|---|---|
{rows}

四种尺寸共 {len(layout['passed'])} 项检查通过：底部中/英与空格在同一行；键区限宽、居中；图标像素包围框居中；不同读音数量的候选卡片宽高与顶边一致；下滑展开详情不上屏；英式/美式和多种读音完整保留；英文真实上屏；单次大写后恢复小写；切回中文能继续输入。拼音通过连续点击屏幕字母键输入，未使用 adb input text 绕过键盘。

![平板横屏候选](screenshots/android-tablet-landscape-candidates.png)

![手机音标详情](screenshots/android-phone-variants.png)

## 输入与主题回归

另外 {len(ui['passed'])} 项输入界面与 {len(theme['passed'])} 项设置检查通过：JNI 中文/英语释义，详情内英音/美音，三主题保留候选，中文和译词上屏，日语/西语切换，翻页，中英模式，部分选词和剩余拼音，崩溃检查，设置页配色，主题重启持久化。

键区位置在空闲和组句期间固定，拼音状态移入工具栏，避免候选出现时按键移动。详情使用垂直 ScrollView，较长释义和发音变体可上下滑动。提示按钮有独立高度，避免三行候选文本被裁切。换肤仍使用键盘内选择条。

## 安装包与数据

`wordtrail-0.1.2-debug.apk`，versionCode 3，{apk.stat().st_size:,} 字节；SHA-256：`{sha}`。

真实 SDK/NDK 构建 arm64-v8a 和 x86_64；Android 8.0+。APK v2/v3 签名和 16 KB 对齐校验通过，使用与 0.1.1 相同的测试签名，能够覆盖安装。应用没有 INTERNET 权限。中文词库、三语言释义及独立英语音标库继续使用原来的已校验数据。

新增界面没有改动 Rust 输入内核和上屏协议。前版共享引擎的 14 项 C ABI、3 项独立音标检查记录保留于 evidence；Windows 已安装补丁和运行证据同样保留。上游 vendor 源码未修改。

## 苹果与待验证项

iOS 源码同步固定候选、中/英底部布局、SF Symbols、下滑详情与平板限宽；无 Mac，尚未 Xcode 编译、签名或真机验证，没有 IPA。

本次四种尺寸是在模拟器中验证，尚未在用户的手机或平板上安装新版，也未验证所有厂商系统与聊天应用。现有同编辑框重启会保留组句；切换不同编辑框仍清空旧会话。音标只针对第一条英语释义，不推测缺词发音，没有发音音频。
'''
    (ROOT/'docs/测试报告.md').write_text(report,encoding='utf-8')
    evidence=ROOT/'docs/evidence'
    for source,dest in [('adaptive-layout-tests.json','adaptive-layout-tests.json'),('adaptive-layout-tests.txt','adaptive-layout-tests.log'),('android-ui-tests.json','android-ui-tests.json'),('android-layout-ui-tests.txt','android-ui-tests.log'),('theme-settings-tests.json','theme-settings-tests.json'),('theme-layout-tests.txt','theme-settings-tests.log')]:shutil.copy2(ROOT/'build'/source,evidence/dest)
    print(json.dumps(dict(layout=len(layout['passed']),input=len(ui['passed']),themes=len(theme['passed']),apk_sha256=sha),indent=2))
if __name__=='__main__':main()
