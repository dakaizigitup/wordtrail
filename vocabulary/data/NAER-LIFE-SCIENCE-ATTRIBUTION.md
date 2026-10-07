# NAER 生命科学术语署名与许可

## 来源与许可

资料提供机构：國家教育研究院（National Academy for Educational Research），《國家教育研究院－生命科學學術名詞》。数据集页面：[data.gov.tw 数据集 15213](https://data.gov.tw/en/datasets/15213)，下载资源见随包 `sources/naer/life-science-dataset.json`。页面将数据许可标为政府資料開放授權條款第1版（Open Government Data License v1.0）：<https://data.gov.tw/license>。

本项目固定保存的来源 CSV 为 `sources/naer/life-science-academic-terms.csv`，包含 9,230 条数据记录，SHA-256：`d8d00e504e1e5feeeb5cad1464c1a1806963689dc43b398594d9e5bdce1556f0`。数据集页面在快照时显示的最近更新日期为 2026-08-12；下载日期、资源链接和快照散列同时记于 `sources/naer/life-science-dataset.json`。

## 本项目筛选与修改

来源中的繁体中文经 OpenCC `t2s` 转换为简体中文。仅筛选单词英文术语，并要求同时具备本机英式或美式 IPA、ECDICT 的精确名词义、本机可输入的拼音候选，以及 NLM MeSH 2026 中精确对应的优选主题词。医学相关候选经逐项审核；每个拼音键最多补 8 条。

本批审查 10 组新增候选，接受 7 组、排除 3 组、暂缓 0 组；其中 1 个英文词头 `ejaculation` 是新词头，新增 2 个医学标签成员。接受映射为：

| 中文 | 英文 | 说明 |
| --- | --- | --- |
| 交媾 | coitus | MeSH 同名主题及 ECDICT 名词义一致 |
| 发炎 | inflammation | MeSH 同名主题及 ECDICT 名词义一致 |
| 射精 | ejaculation | 新增 IPA 词头；MeSH 同名主题及 ECDICT 名词义一致 |
| 知觉 | perception | MeSH 同名主题及 ECDICT 名词义一致 |
| 繁殖 | reproduction | MeSH 同名主题及 ECDICT 名词义一致 |
| 结扎 | ligation | MeSH 同名主题及 ECDICT 名词义一致 |
| 麻痹 | paralysis | MeSH 同名主题及 ECDICT 名词义一致 |

运行时只读取精简映射和标签 TSV，不读取来源 CSV 或审核表。固定来源、筛选输入、输出 SHA-256 和构建器见 `naer-life-science-manifest.json`、`batches/26-naer-life-science-prefilter.tsv`、`batches/26-naer-life-science-candidates.tsv`、`batches/26-naer-life-science-reviewed.tsv` 和 `scripts/build_naer_life_science_batch.py`。
