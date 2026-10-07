# 批次 27：NAER 兽医学术名词

本批从國家教育研究院《獸醫學學術名詞》开放数据中筛选本地可输入且适合医学目标的术语。固定来源有 24,171 条记录，采用政府資料開放授權條款第1版。筛选要求包括：单词英文词头、本机 IPA、ECDICT 精确名词义、真实拼音候选，以及 NLM MeSH 2026 精确主题词。17 组候选逐项复核后接受 6 组、排除 11 组；接受项中 `pallor` 是新英文词头，新增 2 个医学标签成员。

新增映射为：发烧 → `fever`、增殖 → `hyperplasia`、瘫痪 → `paralysis`、肥胖 → `obesity`、苍白 → `pallor`、酗酒 → `alcoholism`。审核排除了扁桃体→`amygdala`、冻疮→`frostbite` 等容易误导的对应，也排除一般化学和环境术语，避免兽医学来源把医学分类标签扩大成杂项标签。

只增加运行时精简 TSV，不扫描 24,171 行 CSV；英文优先顺序仍由用户已选标签决定，中文候选顺序保持不变。重建与逐项证据见 [NAER 兽医学署名说明](../vocabulary/data/NAER-VETERINARY-ATTRIBUTION.md)、[批次清单](../vocabulary/data/naer-veterinary-manifest.json)、[逐项审核表](../vocabulary/data/batches/27-naer-veterinary-reviewed.tsv) 和 `scripts/build_naer_veterinary_batch.py`。
