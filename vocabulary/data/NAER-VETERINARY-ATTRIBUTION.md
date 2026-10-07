# NAER 兽医学术名词署名与许可

## 来源与许可

资料提供机构：國家教育研究院（National Academy for Educational Research），《國家教育研究院－獸醫學學術名詞》。数据集页面：[data.gov.tw 数据集 15461](https://data.gov.tw/en/datasets/15461)，下载资源见随包 `sources/naer/veterinary-dataset.json`。页面将数据许可标为政府資料開放授權條款第1版（Open Government Data License v1.0）：<https://data.gov.tw/license>。

本项目固定保存的来源 CSV 为 `sources/naer/veterinary-academic-terms.csv`，包含 24,171 条数据记录，SHA-256：`cc4599654cbf83fca9ec02b411f08cae8d4d8026925177477c26b97c30837863`。数据集页面在快照时显示的最近更新日期为 2026-06-01；下载日期、资源链接和快照散列同时记于 `sources/naer/veterinary-dataset.json`。

## 本项目筛选与修改

来源中的繁体中文经 OpenCC `t2s` 转换为简体中文。仅筛选单词英文术语，并要求同时具备本机英式或美式 IPA、ECDICT 的精确名词义、本机可输入的拼音候选，以及 NLM MeSH 2026 中精确对应的优选主题词。每个拼音键最多补 8 条。兽医来源中的候选另逐项检查是否属于可供用户选择的医学目标，避免把一般化学、生态或环境词误作临床术语。

本批审查 17 组新增候选，接受 6 组、排除 11 组、暂缓 0 组；其中 1 个英文词头 `pallor` 是新词头，新增 2 个医学标签成员。接受映射为：

| 中文 | 英文 | 说明 |
| --- | --- | --- |
| 发烧 | fever | MeSH 同名主题及 ECDICT 名词义一致 |
| 增殖 | hyperplasia | 病理学义，MeSH 和 ECDICT 名词义一致 |
| 瘫痪 | paralysis | MeSH 和 ECDICT 名词义一致 |
| 肥胖 | obesity | MeSH 和 ECDICT 名词义一致 |
| 苍白 | pallor | 新增 IPA 词头；临床体征义由 MeSH 与 ECDICT 支持 |
| 酗酒 | alcoholism | 常见临床义，MeSH 和 ECDICT 名词义一致 |

运行时只读取精简映射和标签 TSV，不读取来源 CSV 或审核表。固定来源、筛选输入、输出 SHA-256 和构建器见 `naer-veterinary-manifest.json`、`batches/27-naer-veterinary-prefilter.tsv`、`batches/27-naer-veterinary-candidates.tsv`、`batches/27-naer-veterinary-reviewed.tsv` 和 `scripts/build_naer_veterinary_batch.py`。
