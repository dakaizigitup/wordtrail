# 批次25：NAER 医学词条补充

批次25继续审查國家教育研究院《醫學學術名詞》数据集里对应到现有英文词头的译词。批次24的预筛留有591组这类对应；再要求英文词面同时能匹配 NLM MeSH 2026 医学主题、中文词面是 ECDICT 的精确名词义，并且经过批次24后仍未超过候选容量，得到45组待审。逐项审核后接受37组、排除3组、暂缓5组。

本批新增37组中文到英文对应，**没有新增英文词头**；其中18个英文词此前没有医学目标标签，补上医学标签。例子包括 `吸收 → absorption`、`呼吸 → breathing`、`脱水 → dehydration`、`复发 → relapse`、`移植 → transplantation` 和 `呕吐 → vomiting`。对照来源含义和精确词义后，排除了 `冻疮 → frostbite`（应为“冻伤”）及 `肿块 → tumor`（医学词头更适合“肿瘤”）；其余保留的分歧也列在审校表中。

这是对同一 NAER 来源的第二段审校。原数据集授权与署名要求、固定 CSV 和 `[url]` 占位字段限制详见[NAER署名说明](../vocabulary/data/NAER-MEDICAL-ATTRIBUTION.md)。批次输入、MeSH/ECDICT 证据、逐项决定、SHA-256 与构建器见 [`naer-medical-manifest-2.json`](../vocabulary/data/naer-medical-manifest-2.json)、[`25-naer-medical-existing-headwords-prefilter.tsv`](../vocabulary/data/batches/25-naer-medical-existing-headwords-prefilter.tsv)、[`25-naer-medical-existing-headwords-reviewed.tsv`](../vocabulary/data/batches/25-naer-medical-existing-headwords-reviewed.tsv) 和 [`build_naer_medical_batch_2.py`](../scripts/build_naer_medical_batch_2.py)。运行时只把37行映射和18行新增标签编入索引，不读取来源 CSV、MeSH XML 或 ECDICT 文件。Windows 电脑版仍未打包或安装。
