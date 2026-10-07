# 批次35：NAER 教育术语

本批固定国家教育研究院《教育学学术名词》CSV 快照（dataset 6319）。政府资料开放平台将其列为英语与中文教育术语对照表，页面元数据更新于 2026-06-01，采用 Open Government Data License v1.0。固定快照含 2,198 条记录，SHA-256：`b674073b959c749546cac19ef867d27a908ee492d39f69cec4bc4c2dcdcaed57`。来源：[官方数据集页面](https://data.gov.tw/en/datasets/6319)、[授权条款](https://data.gov.tw/license)。

筛选英文单词级词头，要求本机同时具有 ECDICT 精确名词义、英式或美式 IPA、可输入的拼音键和扩展容量。141 组通过精确匹配，其中 105 组已有映射，1 组受每个拼音键最多扩展 8 词的上限限制而未进入审校。其余 35 组尚未映射的候选逐条审校后接受 23 组、排除 10 组、暂缓 2 组，新增 2 个此前没有本地释义映射的英文词头。暂缓 `dismissal → 免职` 和 `school → 学派`，因为来源没有提供足够语境确认其教育义项。其余候选的逐项理由保存在审校表。

另有 130 个英文词头具有来源记录、本机精确名词义、IPA 和拼音证据，加入可单独选择的“教育”分类。这个标签表示词头来自该教育术语表，不表示其所有义项都专属于教育，也不代表完整教育学词表覆盖率。目标选择只调整英文译词优先级，不改变中文候选顺序。

运行时仅载入 23 行精简映射和 130 行分类索引；按键时不会读取 2,198 行来源 CSV。固定数据、SHA-256、审校与构建记录见 [`naer-education-manifest.json`](../vocabulary/data/naer-education-manifest.json)、[`35-naer-education-reviewed.tsv`](../vocabulary/data/batches/35-naer-education-reviewed.tsv)、[`35-naer-education-tags-reviewed.tsv`](../vocabulary/data/batches/35-naer-education-tags-reviewed.tsv)、[署名说明](../vocabulary/data/NAER-EDUCATION-ATTRIBUTION.md)和[`build_naer_education_batch.py`](../scripts/build_naer_education_batch.py)。

本批只更新共享源码和目标设置，没有打包或安装 Android / Windows 版本。最终阶段还需运行完整 Rust 测试、重建两端包并验证输入体验。
