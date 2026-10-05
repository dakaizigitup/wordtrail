# 安卓 0.1.4 系统语音兼容测试

2026-10-05。本版继续使用系统服务，不接独立云 API。iOS 保持 0.1.2，Windows 保持现有 0.1.1 音标补丁。本轮仅修改安卓语音选择、失败提示及设置页。

## 本版已验证

Android 15 x86_64 隔离模拟器运行最终 APK，真实系统权限 UI、RecognitionService Binder 和 InputConnection 完成 34 项检查：

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
- network error exposes service and exact error code
- network failure preserves input and restores keyboard
- no-match error exposes service and exact error code
- no-match failure preserves input and restores keyboard
- language error exposes service and exact error code
- language failure preserves input and restores keyboard
- server error exposes service and exact error code
- server failure preserves input and restores keyboard
- client error exposes service and exact error code
- settings retain actual service and client error without input text
- client failure preserves input and restores keyboard
- disconnected error exposes service and exact error code
- disconnected failure preserves input and restores keyboard
- explicit provider works with stale system default
- single available provider recovers stale default automatically
- missing final result times out and preserves input
- unfinished pinyin is preserved and not replaced by dictation
- changing editors cancels speech and blocks password dictation
- late speech result never enters password editor
- number editor disables microphone
- normal editor re-enables microphone
- no application crash during speech flows

关键用例包括系统默认组件指向已移除服务时，手动服务与自动单服务恢复均能识别；客户端、服务器、断开连接等错误区分具体编号，并记录实际服务；取消、重复回调和换输入框不误插入文字。

识别内容由单独的测试 APK 合成，用于检查流程，不进入生产安装包。**不验证真实麦克风录音、识别准确率，也没有证明用户 iQOO 手机和平板的故障已解决。** 真实根因需要新版错误信息或 USB 调试日志确认；微信输入法语音可用也不能单独证明其开放了系统识别接口。

语音检查分两段完成：主要场景 29 项；最后的编辑器切换场景在测试宿主第一次布局过程中发生触摸位置变化，补上等待布局和麦克风启用的条件后，用独立编辑器脚本完成另外 5 项。同一安装包 SHA 校验一致，主场景执行记录和编辑器补跑记录均保留在 evidence。未将第一次未完成的全流程宣称为一次全部通过。

![具体错误和服务](screenshots/android-speech-error-details.png)

最终 APK 同时通过 16 项中文/译词/音标输入检查和 5 项主题设置检查。本轮合计 55 项。0.1.3 的 52 项手机、横屏平板、竖屏平板和紧凑横屏布局记录保留为历史证据，本轮没有把它们计入新版通过数。

## 安装包

`wordtrail-0.1.4-debug.apk`，versionCode 5，34,001,951 字节；SHA-256 `4dbf5910bed649aa3a23cecd1cb2eb5db56622a05a7dbed74519076d2ada4f36`。包含 arm64-v8a / x86_64，最低 Android 8，目标 Android 15。APK v2/v3 签名及 16 KB 对齐验证通过，沿用旧签名，可覆盖安装。

权限仍仅 RECORD_AUDIO，无 INTERNET。公开服务由系统查询并按用户选择明确绑定；手动服务失效时不静默切换。用户可关闭离线优先，保留使用系统服务可能联网的说明。不保存或自行上传录音，诊断不包含输入框内容。

语音设置为非导出 Activity。失败区维持 72dp，不自动重录；允许设置、切换输入法及返回。相同取消/编辑器保护继续使用。没有调用微信输入法私有接口，切换入口只打开系统输入法选择器。

共享引擎、固定上游、词库、释义和独立音标数据没有修改。源码交付保留许可证、数据来源和完整依赖。苹果未编译、无 IPA；本轮未修改或重新测试已安装桌面程序。
