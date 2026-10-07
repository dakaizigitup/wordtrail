# 计算机词汇补充：批次20

本批使用固定的 [EarsEyesMouth/computerese-cross-references](https://github.com/EarsEyesMouth/computerese-cross-references) MIT 快照，提交 `e92ca7dddf6b8122c7c0807f701fa9e237752506`。上游 README 指明部分项目源自书籍；构建器排除带脚注条目和长解释，只保留297条短小、无来源脚注的单词条作为候选发现材料。由于其余项目也没有逐条注明早期来源，因此不直接照单全收。

从筛选结果中找到75组精确 ECDICT 义项/词性、本机拼音和 IPA 候选；62组映射原本已有，逐条审校后新增13组中文—英文对应：

| 中文 | 英文 | 词性 | 复核语境 |
| --- | --- | --- | --- |
| 主机 | mainframe | n. | 计算机硬件 |
| 前提 | precondition | n. | 编程与逻辑条件 |
| 单元 | cell | n. | 表格、存储或硬件单元 |
| 安全 | security | n. | 计算机与信息安全 |
| 崩溃 | crash | n. | 程序崩溃 |
| 指令 | directive | n. | 编译器、语言或配置指令 |
| 探测器 | probe | n. | 系统诊断或网络探测 |
| 约定 | convention | n. | 软件/API/编码约定 |
| 缺陷 | bug | n. | 软件缺陷 |
| 节流 | throttle | v. | 限流 |
| 装箱 | box | v. | 编程中的装箱操作 |
| 解析 | resolution | n. | 名称或 DNS 解析 |
| 设备 | device | n. | 计算机或外围设备 |

这13项都是已存在英文词头的新增中文义项；**新英文词头为0**。另有55个原先尚无计算机类别的英文词头新增计算机标签；泛化程度过高的 `free`、`erosion`、`community` 未贴标签。分类标签不代表完整专业词表覆盖率。

运行索引只载入13行映射与55行标签，不载入整份 README；中文候选顺序保持不变。逐项证据、排除理由、固定输入/输出散列、来源许可及复建脚本见[署名与来源说明](../vocabulary/data/COMPUTERESE-ATTRIBUTION.md)、[`20-computerese-reviewed.tsv`](../vocabulary/data/batches/20-computerese-reviewed.tsv)、[`20-computerese-evidence.tsv`](../vocabulary/data/batches/20-computerese-evidence.tsv)和[`computerese-manifest.json`](../vocabulary/data/computerese-manifest.json)。本批已接入共享源码，尚未打包；Rust 单元测试仍需在具备 MSVC 链接器的环境中执行。
