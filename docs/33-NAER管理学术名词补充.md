# 批次33：NAER 管理学学术名词

本批固定国家教育研究院《管理学学术名词》（dataset 15440）快照。官方数据页元数据更新于2026-08-12，CSV共有12,936条，文件SHA-256为`2f323ca6b4cf2a5a83dc01b1b044551c809e73f2f025858fd0b69c7b99e2bf4d`；来源和政府资料开放授权条款第1版署名见[NAER管理词表说明](../vocabulary/data/NAER-MANAGEMENT-ATTRIBUTION.md)。

筛选单词级英文词头，并要求本机同时具备英式或美式音标、可输入的拼音键和完全一致的ECDICT名词义；繁体中文经OpenCC转简体后按完整词面匹配。共285组满足这些本地条件，238组原已映射；47组新映射候选逐项审校，纳入41组、排除5组、暂缓1组，纳入项涉及11个此前没有本地释义映射的英文词头。每个中文键最多增加8个扩展译词；本批47组新候选均通过容量检查。

对来源中具有本地精确词义、拼音和音标的274个英文词头添加商务来源成员，其中199个是新增成员。此标签表示该词头出现在NAER管理学术名词表中；一个词可同时保留考试、计算机、医学和其他商务来源标签。运行时只载入41条精简映射和274条紧凑标签，不读取研究CSV，也不改变中文候选顺序。

逐项映射决定见[`33-naer-management-reviewed.tsv`](../vocabulary/data/batches/33-naer-management-reviewed.tsv)，标签归属见[`33-naer-management-tags-reviewed.tsv`](../vocabulary/data/batches/33-naer-management-tags-reviewed.tsv)。完整筛选表、SHA-256和可重复构建命令见[`naer-management-manifest.json`](../vocabulary/data/naer-management-manifest.json)与[`build_naer_management_batch.py`](../scripts/build_naer_management_batch.py)。
