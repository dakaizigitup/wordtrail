# 批次34：NAER 行政学学术名词

本批固定国家教育研究院《行政学学术名词》（dataset 15262）CSV 快照。政府资料开放平台页面元数据更新于 2026-08-12，来源共 3,737 条记录，采用政府资料开放授权条款第 1 版。许可与数据集说明见[官方页面](https://data.gov.tw/dataset/15262)和[授权条款](https://data.gov.tw/license)。固定快照 SHA-256：`8faf844b2393fbb27f432a8a5df8e4194c6e64c8a0c7754b0a6242a7b2e4f05b`。

筛选英文单词级词头，并要求本机同时具备精确 ECDICT 名词义、英式或美式 IPA、可输入拼音键和每键扩展容量。共 79 组候选满足这些条件，其中 61 组已映射；剩余 18 组逐项审校后接受 17 组、暂缓 1 组，新增 4 个此前没有本地释义映射的英文词头。暂缓项为 `reconciliation → 调解`：该中文义与 mediation 更直接对应，缺少更窄语境时不加入。

76 个有本地精确词义、拼音和音标证据的来源词头加入独立“行政学”分类。分类只表示该词出现在 NAER 行政学术语表中，不声称覆盖整个公共管理或政治学领域。设置支持与考试、计算机、商务和医学目标同时多选；候选排序仍只优先匹配目标的英文译词，中文候选顺序不变。

运行时仅载入 17 行精简映射和 76 行分类索引，不扫描 3,737 行来源 CSV。逐项决定、标签证据、清单和可重复构建命令见 [`34-naer-administration-reviewed.tsv`](../vocabulary/data/batches/34-naer-administration-reviewed.tsv)、[`34-naer-administration-tags-reviewed.tsv`](../vocabulary/data/batches/34-naer-administration-tags-reviewed.tsv)、[`naer-administration-manifest.json`](../vocabulary/data/naer-administration-manifest.json) 和 [`build_naer_administration_batch.py`](../scripts/build_naer_administration_batch.py)。

索引仍在初始化时一次载入，按英文词头哈希查询；本批运行数据为 93 行。当前主机没有 MSVC `link.exe`，全量 Rust 单测及 p50/p95 查询耗时尚未验证；源码解析、候选审计和数据散列检查已通过，待最终构建阶段补做完整性能与运行测试。
