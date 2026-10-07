# 批次37：NAER 教育学研究术语

本批固定国家教育研究院《Terminology of Educational Studies》CSV（dataset 15367）。[官方页面](https://data.gov.tw/en/datasets/15367)将其列为英汉教育术语资料，采用 Open Government Data License v1.0，页面元数据更新于 2026-08-12 14:19。快照于 2026-10-07 固定，含 2,740 条数据记录，SHA-256：`6a72f8970c4e86999f53063866625df6852b93158b4a425b2a4bd0cab3b87d45`。[授权条款](https://data.gov.tw/license)

筛选英文单词词头，要求本机同时有 ECDICT 精确名词义、英式或美式音标、可输入的拼音键。186 组通过精确证据筛选，其中 164 组原已有中英对应，1 组受每个拼音键最多扩展 8 词的运行时上限限制；剩余 21 组逐项审校后接受 5 组、排除 14 组、暂缓 2 组，新增 2 个此前没有本地映射的英文词头。接入的对应为：合理化 → `rationalization`、回忆 → `recollection`、学派 → `school`、美学 → `esthetics`、遗传 → `inheritance`。其余条目保留逐项排除或暂缓理由。

另有 171 个英文词头具有来源记录、本机精确名词义、IPA 与拼音证据；其中 42 个此前没有教育标签。本批把它们归入已有“教育”目标，不新增重复设置项。来源成员关系不表示英文词头的所有义项都专属于教育，也不代表完整教育学词表覆盖率。选中目标只优先对应的英文译词，不改变中文候选顺序。

运行时仅载入 5 行映射和 171 行来源标签，不扫描 2,740 行原始 CSV。固定数据、逐项审校、SHA-256 与可重复构建记录见 [`naer-educational-studies-manifest.json`](../vocabulary/data/naer-educational-studies-manifest.json)、[`37-naer-educational-studies-reviewed.tsv`](../vocabulary/data/batches/37-naer-educational-studies-reviewed.tsv)、[`37-naer-educational-studies-tags-reviewed.tsv`](../vocabulary/data/batches/37-naer-educational-studies-tags-reviewed.tsv)、[署名说明](../vocabulary/data/NAER-EDUCATIONAL-STUDIES-ATTRIBUTION.md)和[`build_naer_educational_studies_batch.py`](../scripts/build_naer_educational_studies_batch.py)。

本批只扩展共享词库源码和审计说明，没有打包或安装客户端。电脑版仍按用户安排，等词汇批次完成后再处理。
