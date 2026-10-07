# 批次 26：NAER 生命科学术语

本批从國家教育研究院《生命科學學術名詞》开放数据中筛选可输入的医学、生殖与临床相关术语。固定来源有 9,230 条记录，采用政府資料開放授權條款第1版。筛选要求包括：单词英文词头、本机 IPA、ECDICT 精确名词义、真实拼音候选，以及 NLM MeSH 2026 精确主题词。候选逐项审查后，10 组进入复核，接受 7 组、排除 3 组；接受项中 `ejaculation` 是新英文词头，新增 2 个医学标签成员。

这 7 组映射为：交媾 → `coitus`、发炎 → `inflammation`、射精 → `ejaculation`、知觉 → `perception`、繁殖 → `reproduction`、结扎 → `ligation`、麻痹 → `paralysis`。拒绝项包括范围过宽的“酒精”→ `ethanol`，以及超出本批医学标签范围的植物发芽、动物交尾术语。

只增加运行时精简 TSV，不扫描 9,230 行 CSV；英文优先顺序仍由用户已选标签决定，中文候选顺序保持不变。重建与逐项证据见 [NAER 生命科学署名说明](../vocabulary/data/NAER-LIFE-SCIENCE-ATTRIBUTION.md)、[批次清单](../vocabulary/data/naer-life-science-manifest.json)、[逐项审核表](../vocabulary/data/batches/26-naer-life-science-reviewed.tsv) 和 `scripts/build_naer_life_science_batch.py`。
