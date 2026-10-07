<div align="center">
  <img src="branding/wordtrail-warm-icon.png" width="112" alt="词伴暖色小书灵图标">
  <h1>词伴 Wordtrail</h1>
  <p>好好打字，顺便认识一个新单词。</p>
  <p>Windows 音标增强 · Android 双语键盘与离线语音 · iOS 键盘源码</p>
</div>

词伴基于 [青简 qingjian](https://github.com/qingjian-team/qingjian) 开源内核，输入中文时，在候选旁显示外语释义、词性和英语音标，让学习融入日常打字。这是个人维护的独立改版项目，**不是青简官方产品**。

## 下载

GitHub 最新发布版为 **v0.1.23**（Android 0.1.23、Windows 补丁 0.1.16）。当前本地开发源码已推进到 Android **0.1.28**、Windows 补丁 **0.1.21**：加入六类考试目标、计算机/商务/医学目标及分批扩充词汇；尚未发布 Windows 安装补丁。下表链接仍指向上一版公开发行包。

| 下载 | 用途 |
| --- | --- |
| [Android 安装包](https://github.com/dakaizigitup/wordtrail/releases/download/v0.1.23/wordtrail-0.1.23-debug.apk) | Android 8.0+，64 位 ARM 手机/平板；已含离线语音模型 |
| [Windows 音标与考试词汇补丁](https://github.com/dakaizigitup/wordtrail/releases/download/v0.1.23/wordtrail-windows-ipa-0.1.16.zip) | 已安装官方青简 Windows 0.1.4 的用户；提供安装和恢复脚本 |
| [完整对应源码](https://github.com/dakaizigitup/wordtrail/releases/download/v0.1.23/wordtrail-0.1.23-source.zip) | Windows、Android、iOS 源码及固定第三方依赖/词库；不含工具链和私钥 |
| [SHA-256 校验和](https://github.com/dakaizigitup/wordtrail/releases/download/v0.1.23/SHA256SUMS.txt) | 核对发布附件 |

后续版本请查看 [Releases](https://github.com/dakaizigitup/wordtrail/releases) 和 [CHANGELOG](CHANGELOG.md)。**目前没有 iOS IPA 或 macOS 音标补丁。**

本地共享词库继续按批次扩充。批次28固定 [WordLevel TOEFL/IELTS 学术词表](https://github.com/gungorkaya-eng/toefl-essential-vocabulary-dataset)，946个有本地中文释义和音标的词头加入双考试标签；11条可输入候选逐项处理后，接受4组映射（3个新英文词头）、排除6组、暂缓1组。该社区词表不是官方考纲；GitHub 仓库声明 MIT，Mendeley 记录声明 CC BY 4.0，因此项目同时保留 MIT 文本及 [WordLevel](https://wordlevel.net) 链接署名。该批尚未打包发布，电脑版仍按安排暂不安装。详见[批次28说明](docs/28-WordLevel考试词汇.md)和[来源记录](vocabulary/data/WORDLEVEL-ATTRIBUTION.md)。

## 当前功能

| 功能 | Android 本地 0.1.28 | Windows 本地 0.1.21 | iOS 源码 |
| --- | --- | --- | --- |
| 中文拼音候选与外语释义 | 已实现 | 复用官方青简 | 已实现，未编译 |
| 英语 / 日语 / 西班牙语释义 | 每次显示一种 | 复用官方设置 | 每次显示一种，未验证 |
| 英式 / 美式英语音标 | 展开候选详情查看 | 各英语释义旁注 | 展开详情，未验证 |
| 英语考试目标、多标签与译词优先 | 六类考试加三类专业目标 | 六类考试加三类专业目标 | 已加入源码，未验证 |
| 中文 / 英文本机离线语音 | 已实现，不依赖系统语音服务 | 未新增 | 未新增 |
| 青绿 / 粉紫 / 深色主题 | 可切换 | 官方外观 | 已加入源码，未验证 |
| 手机 / 平板自适应 | 已实现 | 不适用 | 已加入源码，未验证 |

Android 同时提供中英切换、数字/符号键盘、主动收起按钮、紧凑候选行、可滚动的释义/多音标详情。新译词标橙、熟悉译词变灰；保留本地学习机制。

**本地开发源码已支持六类考试目标与计算机、商务、医学三类专业目标**，可多选并保留同词多标签。命中目标的英文译词优先，中文候选顺序不变；原有译词仍保留。社区收录标签不等于官方完整考试范围、考试成绩、个人水平或完整专业词表。详见 [0.1.8 使用说明](docs/0.1.8词汇目标.md)、[专业词汇首批](docs/0.1.24专业词汇首批.md)、[计算机术语第二段](docs/0.1.25计算机术语第二段.md)和[MeSH医学词汇批次](docs/21-MeSH医学词汇.md)。

0.1.23 延续前两批新增的 **2,291 组**考试词汇映射，不改变中英释义；另外新增 **407 个拼音键**，只让词库里已经存在的译词更容易按中文拼音输入。按实际候选面修正批次12基线后，四级/六级/专四/专八/托福/雅思拼音可达率为 **97.74% / 96.67% / 96.15% / 94.05% / 90.01% / 94.91%**；专四/专八/托福/雅思映射覆盖率仍为 **97.56% / 95.85% / 90.81% / 96.20%**。社区词表并非官方完整考纲，也不保证译词出现在第一页。来源、许可证、逐键记录及筛选限制见 [0.1.23补词记录](docs/0.1.23专四专八雅思托福补词.md)、[归属说明](vocabulary/data/EXAM-TARGETS-ATTRIBUTION.md) 与[分批计划](docs/分批补词计划.md)。

本地0.1.24批次首次加入计算机、商务、医学标签，并新增10组经人工复核的医学映射。0.1.25使用固定 CC BY-SA 4.0 计算机术语表再加入26组可达映射，其中5个是新英文词头；两条不准确的 `value → 变量/常量` 均已排除。0.1.26从固定 MIT 许可 FIBO 快照审查87个金融商务候选，接入75个商务标签归属，其中72个为新增标签、没有新增中英映射或词头。0.1.27再从固定 MIT 许可 Better Quant Wiki 双语金融术语表加入7组映射（3个新英文词头）。0.1.28从 CFPB 官方消费金融中英词表筛出246组拼音、音标和 ECDICT 均可核验的唯一对应，映射达到223组/90.65%；新增67组映射（13个新英文词头）和193个商务标签归属，22条语境未审定候选继续暂缓。该比率只覆盖严格筛出的候选子集，不代表整份 CFPB 词表覆盖率。后续共享词库源码批次19增加47组金融映射（12个新英文词头）及41个商务标签；批次20增加13组计算机中文义项（0个新英文词头）及55个计算机标签；批次21新增75组 MeSH 医学映射（74个新英文词头）和1,079个医学标签成员。MeSH 只提供英文主题范围，中文短义由 ECDICT MIT 核验；256组候选中7组排除、174组暂缓，没有宣称医学总覆盖率。批次19–21尚未打包或安装；Rust 测试需在具备 MSVC 链接器的环境中补跑。此前 Android 测试 APK 在本地构建；Windows 依照你的安排尚未安装。详见[批次14记录](docs/0.1.24专业词汇首批.md)、[批次15记录](docs/0.1.25计算机术语第二段.md)、[批次16记录](docs/0.1.26商务金融标签.md)、[批次17记录](docs/0.1.27商业金融词汇.md)、[批次18记录](docs/0.1.28商业金融词汇.md)、[批次19记录](docs/19-finance-i18n金融词汇.md)、[批次20记录](docs/20-computerese计算机词汇.md)、[批次21记录](docs/21-MeSH医学词汇.md)和[0.1.28测试报告](docs/0.1.28测试报告.md)。

共享词库源码从 Wikidata CC0 × MeSH 增加批次22–23共44组医学译词；批次24–25从國家教育研究院《醫學學術名詞》接受94组映射、增加75个医学标签成员。批次26–27再从 NAER 生命科学与兽医学开放数据逐项审核 27 组候选，接受13组映射、排除14组；其中2个英文词头是本地 IPA 词库原先没有的，另增加4个医学标签成员。总数据源许可为政府資料開放授權條款第1版；每条仍需本机拼音、IPA、ECDICT 名词义和 MeSH 证据，兽医表中的一般化学、生态和环境词没有混入医学类别。来源快照 SHA-256、筛选、审核与构建命令见[批次22](docs/22-Wikidata医学译词.md)、[批次23](docs/23-Wikidata医学译词补充.md)、[批次24](docs/24-NAER医学学术词汇.md)、[批次25](docs/25-NAER医学词条补充.md)、[批次26](docs/26-NAER生命科学词汇.md)、[批次27](docs/27-NAER兽医学词汇.md)及[NAER署名说明](vocabulary/data/NAER-MEDICAL-ATTRIBUTION.md)、[生命科学说明](vocabulary/data/NAER-LIFE-SCIENCE-ATTRIBUTION.md)、[兽医学说明](vocabulary/data/NAER-VETERINARY-ATTRIBUTION.md)。这些共享源码批次尚未打包发布；Windows 电脑版仍按安排暂不安装。

## 安装与使用

### Android

1. 下载 APK，在手机文件管理器打开安装。已有同签名词伴版本可直接覆盖安装，保留设置与学习数据。
2. 打开“词伴输入法”，点“① 启用词伴键盘”，再点“② 切换到词伴”。
3. 在输入框输入 `nihao`：候选显示“你好”和 `hello`。点候选输入中文；长按候选输入译词。
4. 点候选小箭头或向下滑查看完整释义、词汇标签及英式/美式音标；点“EN 译词”切换学习语言。
5. 在首页“词汇学习目标”选择考试或专业领域，可多选；全部词汇保留，命中目标的译词优先。详情可逐条输入译词。
6. “中/英”切换输入模式，◐ 切换主题，右上角向下箭头收起键盘。点击麦克风后授权录音，说话并点“完成”插入文字；“取消”不会插入。

语音默认使用随包 SenseVoice int8 + sherpa-onnx + Silero VAD，本机处理，不上传或保存录音。首次准备模型需要额外空间，建议预留约 1 GB。可选系统语音只在设备提供公开识别服务时可用；选择该方式时服务可能联网。

更多操作见 [安装与测试指南](docs/安装与测试指南.md)。

### Windows

1. 从 [青简官方 v0.1.4](https://github.com/qingjian-team/qingjian/releases/tag/v0.1.4) 安装 Windows 版。
2. 下载并完整解压本项目的 Windows 音标补丁，结束正在输入的拼音，运行 `install.cmd`，按系统提示授予管理员权限。
3. 用 `Win + 空格` 切换到青简，在偏好设置选择英语；输入 `nihao` 即可看到英语释义旁的英式/美式音标。
4. 运行补丁目录里的 `settings.cmd` 多选考试或专业词汇目标，保存后约一秒生效。
5. 译词超过两条时，按 `Ctrl+Alt+候选序号` 轮换查看，原译词输入快捷键输入当前显示的第一/第二条；输入新的拼音后恢复目标排序。
6. 若要恢复安装前的服务，运行 `rollback.cmd`。保留整个补丁目录及安装时生成的 `backup/`。

补丁只替换候选窗口服务并增加音标文件，保留原输入法 DLL、输入协议、词库与用户数据。补丁尚无官方数字签名；管理员宿主窗口等特殊场景未充分验证。详见 [Windows 补丁说明](docs/电脑版音标补丁.md)。

### iOS

仓库提供宿主应用与系统键盘扩展源码、音标/考试标签和同款图标资源。需要 Mac、Xcode 和签名后才能安装；本项目尚未执行 iOS 编译或真机验证，**不要将源码支持理解为已有可安装版本**。

## 界面预览

  <img src="docs/screenshots/android-0.1.10-goals.png" width="230" alt="Android 英语学习目标多选">
<img src="docs/screenshots/android-0.1.10-priority.png" width="230" alt="Android 新增六级译词优先与多标签候选">

<img src="docs/screenshots/android-0.1.10-expanded.png" width="230" alt="新增译词详情滚动与逐条输入">

<img src="docs/screenshots/desktop-0.1.4-expansion.png" width="620" alt="Windows 真实候选窗口音标">

从 0.1.9 起，候选、详情和设置里均移除 A1–C2，详见 [标签精简说明](docs/0.1.9标签精简.md)。

更多 [主题预览](docs/主题预览.html)、[本版测试报告](docs/0.1.23测试报告.md)、[上一版补词记录](docs/0.1.22专四专八雅思托福补词.md) 与 [初版测试报告](docs/测试报告.md)。

## 实现基底

中文候选来自青简拼音内核与本地词库。英文、日文和西班牙文释义是随包的离线数据，按候选词查表；英语音标来自独立 IPA 词典，共 **147,488 个词条**，按单词查询英式 RP / 美式 GA 数据。当前界面只显示考试收录标签，不再显示 A1–C2 参考等级。

日常拼音、释义、音标、考试标签和默认语音都在本机处理。Android 应用没有 `INTERNET` 权限；开发构建时的数据下载与安装包内的日常运行是不同阶段。

这仍是实验版：没有九宫格、手写、滑行输入、表情面板或完整的学习统计页，也没有移植桌面的整句神经模型。当前发布以可用的输入与辅助学习为主。

## 开发与构建

| 目录 | 内容 |
| --- | --- |
| `native/` | 共享 Rust 会话、候选、JSON / C ABI / Android JNI 与分级 |
| `android/` | Java 系统输入法、设置界面和离线语音 JNI |
| `ios/` | SwiftUI 宿主、UIKit 键盘扩展与 XcodeGen 工程描述 |
| `desktop/` | Windows 音标增强服务 |
| `vocabulary/` | 六类考试多标签、实际扩词索引与共享排序规则 |
| `upstream/` | 固定青简内核的小型校验补丁，保留普通两条释义上限 |
| `pronunciation/` | 独立英式 / 美式音标数据与查询代码 |
| `vendor/qingjian/` | 固定版本的上游源码和数据来源说明 |
| `scripts/` | 构建、数据准备、打包与发布 |
| `tests/` | 引擎、输入连接、布局、快速触屏和语音流程检查 |

Git 仓库保留日常可维护源码；大型构建产物、第三方依赖副本、生成词库和模型权重不提交 Git。**Release 的完整源码 ZIP 包含对应的第三方源码和数据**，用于审查、构建及保留完整许可。

扩词采用精简索引，首次初始化后按中文词面查表，不会在每次按键时扫描研究词典或 WordNet。Wiktionary、CC-CEDICT 与 OpenEtymology 派生数据分别保留许可、署名和来源记录；运行数据、固定名单散列和审校记录随源码包提供。WordNet 只用于开发构建时的拼写/同义校验。社区词表不等于官方完整考试范围。

克隆后，先恢复与本版匹配的依赖和词库：

```powershell
git clone --recurse-submodules https://github.com/dakaizigitup/wordtrail.git
cd wordtrail
python scripts/bootstrap_dependencies.py
python scripts/bootstrap_vocab_tools.py
```

也可指定已下载的对应源码：

```powershell
python scripts/bootstrap_dependencies.py --source-zip C:\Downloads\wordtrail-0.1.23-source.zip
```

`bootstrap_vocab_tools.py` 另行恢复固定 SHA-256 的 OpenCC Python 0.1.7，仅供考试词表构建时繁简转换。构建还需要 Python 3.11+、Rust 1.96、JDK 21、Android SDK 35 / Build Tools 35.0.0 / NDK 28.2.13676358，Windows 服务构建还需对应 GNU 链接工具。现有 PowerShell 脚本默认读取作者本机的工具链配置，**其他电脑需先调整路径和 `toolchain.json`**；仓库并未提供完整工具链安装器。

Android：`scripts/build_android.ps1`；Windows：`scripts/build_desktop.ps1`；iOS：Mac 上执行 `scripts/build_ios.sh`。详细步骤、来源固定方式和验证边界见 [开发说明](docs/开发说明.md)。

## 后续版本

六类考试目标已接入；计划加入更多专业词汇目标、可选词汇包、学习统计与复习功能，并继续优化离线语音和键盘体验。词表来源、许可、分级依据和跨平台行为会逐项确定，未完成的功能不会写成已实现。详见 [ROADMAP](ROADMAP.md)。

欢迎提交 Issues 与 Pull Request，见 [CONTRIBUTING](CONTRIBUTING.md)。

2026-10-05 已完成第一阶段 [词库调研与多标签设计](docs/词库调研与多标签设计.md)，包括实际数据去重、来源检查与索引速度原型。2026-10-06 已接入六类目标、多标签及实际扩词，见 [0.1.10 说明](docs/0.1.10实际扩词.md)。

## 来源与许可

新增代码采用 **GPL-3.0-or-later**，见 [LICENSE](LICENSE)。青简固定为 v0.1.4、提交 `f7abaefcb1a3aeaca5c01692941a64a7b1f43eb5`；本项目使用独立名称与原创图标，没有使用青简官方 logo。

音标、CEFR 词表、释义数据、语音模型及依赖各有来源和许可，不能统称 GPL。完整声明与许可全文见 [NOTICE.txt](NOTICE.txt)、[Windows 许可声明](desktop/NOTICE.txt) 和 [第三方语音资源](third-party/sherpa-onnx/)。修改数据或分发衍生版本时请保留对应署名、许可及源码义务。
