# GitHub 项目调研与选型

美化更新参考 [FlorisBoard 主题文档](https://docs.florisboard.org/themes/) 中关于字体、边距、颜色及主题切换的组织方式，并查看了 [官方键盘与主题展示](https://florisboard.org/)。本项目的三套配色、圆角键帽、候选层次、卡片设置页和地球图标均自行实现，没有复制第三方皮肤、品牌或位图素材。

核查日期：2026-10-05。以项目仓库及其许可文件为依据，避免把早期许可证套用到当前商业版本。

| 项目 | 平台/作用 | 核查结果 | 本次借鉴 |
|---|---|---|---|
| [qingjian-team/qingjian](https://github.com/qingjian-team/qingjian) | 桌面输入法、Rust 引擎 | v0.1.4 代码 GPL-3.0-or-later；名称与 logo 不授权；官方移动版请求见 [issue 107](https://github.com/qingjian-team/qingjian/issues/107) | 实际复用 core、dictionary、translate、learning、format，保留上游原源码 |
| [osfans/trime](https://github.com/osfans/trime) | Android Rime 输入法 | GPL-3.0 | 参考系统 IME 生命周期、候选区、平台与引擎分层；未复制代码 |
| [fcitx5-android/fcitx5-android](https://github.com/fcitx5-android/fcitx5-android) | 原生引擎移植 Android | 仓库 LICENSE 为 LGPL-2.1，部分依赖另有许可 | 参考原生引擎与手机键盘分离、ABI 打包思路；未复制代码 |
| [florisboard/florisboard](https://github.com/florisboard/florisboard) | Android 键盘界面 | Apache-2.0 | 可参考键盘布局、交互与设置；本次界面用 Android 原生组件自行实现 |
| [imfuxiao/Hamster](https://github.com/imfuxiao/Hamster) | iOS Rime 键盘扩展 | 当前公开仓库含 MIT 许可；README 明确表示后续商业版本不再开源 | 可参考 iOS 宿主应用/键盘扩展组织；不能把当前商店新版当作持续开源代码 |
| [KeyboardKit/KeyboardKit](https://github.com/KeyboardKit/KeyboardKit) | iOS 键盘 SDK | 当前主线为商业二进制 SDK，不能按旧版 MIT 描述 | 未引入，直接使用 UIKit 的 UIInputViewController |

## 为什么保留青简内核

用户需要的是青简的双语候选与学习机制。改用 Rime 或 Fcitx 作为核心，需要重新实现释义、词频与熟悉度适配。青简已有平台无关 Rust 引擎，因此共享这部分逻辑，Android 用 JNI 接入，iOS 用 C ABI 接入，两端只处理按键和界面。

Android 使用 [InputMethodService 官方接口](https://developer.android.com/develop/ui/views/touch-and-input/creating-input-method)。iOS 使用 [Custom Keyboard 官方机制](https://developer.apple.com/library/archive/documentation/General/Conceptual/ExtensibilityPG/CustomKeyboard.html)，并遵循 [Open Access 配置说明](https://developer.apple.com/documentation/uikit/configuring-open-access-for-a-custom-keyboard)：当前没有网络和 App Group 写入需求，故 RequestsOpenAccess 为 false，学习数据保存在扩展自己的目录。

## 难度判断

做出“全拼 + 双语候选”的安卓测试版难度中等，原生引擎跨编译和输入框状态同步是主要工作。苹果端更费功夫：需要 Mac/Xcode 编译签名，还要实测键盘扩展的内存、生命周期、屏幕尺寸与输入宿主兼容性。共享核心能够减少两端重复开发，但不能代替平台验证。

做成日常主力输入法的难度明显更高，还需补齐输入纠错、长句、滑动/长按细节、更多布局、无障碍与多机型测试。当前交付针对首版核心功能，不承诺成熟输入法的所有能力。

## 英语音标来源

[open-dict-data/ipa-dict](https://github.com/open-dict-data/ipa-dict) 提供离线国际音标数据。固定提交 43c3570eb3553bdd19fccd2bd0091534889af023，英式 RP 来源 leoboiko/ipacards（GPL-3.0-only），美式 GA 来源 lingz/cmudict-ipa（MIT）。本次按单词合并独立音标库，保留原始发音变体，未在线请求翻译。
