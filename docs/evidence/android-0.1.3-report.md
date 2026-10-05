# 词伴安卓 0.1.3 测试报告

日期：2026-10-05。此次只为安卓新增系统语音输入，iOS 键盘功能保持 0.1.2；Windows 仍使用 0.1.1 音标补丁。

## 安卓语音流程

Android 15 x86_64 隔离模拟器安装最终 APK，通过真实系统权限对话框、RecognitionService Binder 和 InputConnection，完成 22 项检查。

- missing recognition service explains setup and preserves input
- missing service returns to normal typing
- denied microphone permission does not start recognition
- permission denial leaves typing available
- permission grant does not automatically record
- system recognition warns before recording
- partial transcript is previewed without being inserted
- Chinese speech uses zh-CN and allows system engine fallback
- finish stops recognizer and commits final transcript
- English locale and duplicate results commit only once
- cancel discards partial and late final results
- hiding keyboard cancels recording without inserting late result
- network failure preserves input and restores keyboard
- no-match failure preserves input and restores keyboard
- language failure preserves input and restores keyboard
- missing final result times out and preserves input
- unfinished pinyin is preserved and not replaced by dictation
- changing editors cancels speech and blocks password dictation
- late speech result never enters password editor
- number editor disables microphone
- normal editor re-enables microphone
- no application crash during speech flows

识别回调由单独的测试 APK `org.wordtrail.speechtest` 合成，用于可重复地触发中文、英文、网络失败、无结果、重复与迟到结果。测试 APK 不进入词伴安装包。测试保持 UI 自动化连接稳定，避免辅助服务反复连接导致系统重启输入视图。测试后恢复原有识别服务配置及被暂时停用的模拟器服务。

**这些检查验证接入流程和输入框安全，不验证真实麦克风录音或识别准确率。** 语音预览截图使用测试回调，不能当成实际录音识别效果。部分厂商没有向第三方提供系统识别服务，仍需要真机确认。

![语音预览流程测试](screenshots/android-speech-listening.png)

## 布局、输入与主题回归

最终 APK 同时完成 52 项自适应布局操作、16 项输入和 5 项设置检查。当前合计 95 项通过。

| 配置 | 像素 | 密度 |
|---|---|---|
| phone | 1080x2160 | 440 dpi |
| tablet-landscape | 2560x1600 | 240 dpi |
| tablet-portrait | 1600x2560 | 240 dpi |
| compact-landscape | 1920x1080 | 440 dpi |

检查键区限宽居中、统一候选尺寸、音标下滑与滚动、中英切换、单次大写、图标居中、原生双语候选、中文与译词上屏、日语西语切换、翻页和主题持久化。拼音经屏幕真实点击输入，没有绕过输入法直接向输入框填入拼音。

## 安装包与权限

`wordtrail-0.1.3-debug.apk`，versionCode 4，34,001,951 字节；SHA-256：`2f4a8de90742e7aede4d0debacf6db7902c9b4925bde5419b9b95bfd3782ec18`。

arm64-v8a + x86_64，Android 8.0+；APK v2/v3 签名及 16 KB 对齐通过。沿用旧版本测试签名，可覆盖安装。

新增 RECORD_AUDIO 和系统识别服务查询声明，没有 INTERNET 权限。词库、译词、音标及学习仍在本机运行；独立的系统识别服务可以使用自己的网络权限，因此语音不能承诺全程离线。默认先试 API 31+ 设备离线识别，失败或缺失时，用户允许后使用系统服务，并持续显示“可能联网”。

临时识别结果只显示于候选区，最终结果插入一次；键盘隐藏、换输入框、取消和销毁会 cancel / destroy 并使会话 token 失效。密码与数字框禁止语音；未完成拼音会保留并提示先选词。词伴没有保存或自行上传录音的代码。

## 数据、苹果与其他平台

共享 Rust 引擎、固定上游、中文词库、三语言释义、147,488 条独立英语音标保持原内容。前版 14 项 C ABI、3 项独立音标以及 Windows 补丁验证记录保留在 evidence；此轮未重新测试未修改的桌面程序。

苹果端仍提供三主题、平板布局及音标源码，未增加语音；缺少 Mac，尚未编译或验证，也没有 IPA。此次新版尚未安装到用户的真实手机和平板。语音语言包、第三方聊天应用、麦克风质量、网络条件和各厂商服务都需要真机试用。
