# 批次36：NAER 心理学术语

本批固定国家教育研究院《心理学学术名词》CSV（dataset 15167），来源页面介绍其为英汉心理学术语资料，采用 Open Government Data License v1.0。快照于 2026-10-07 固定，含 11,085 条数据记录，SHA-256：`d603fce3628389aa849c73f1af4104653357e715fb82946e35b67507d992f166`。来源：[官方数据集页面](https://data.gov.tw/en/datasets/15167)、[授权条款](https://data.gov.tw/license)。

筛选英文单词词头，要求本机同时有 ECDICT 精确名词义、英式或美式音标、可输入的拼音键。485 组通过精确证据筛选，其中 365 组原已有中英对应，2 组受每个拼音键最多扩展 8 词的运行时上限限制；剩余 118 组逐项审校后接受 89 组、排除 16 组、暂缓 13 组，新增 14 个此前没有本地映射的英文词头。存在同义或范围歧义的条目保留逐项原因；对“分离”只接入更具体的 `dissociation`，把另一个可选译词 `separation` 暂缓，避免超过该拼音键的容量。

另有 443 个英文词头具有来源记录、本机精确名词义、IPA 与拼音证据，加入独立“心理学”来源标签。该标签表示来源成员关系，不代表词头所有义项都专属于心理学，也不代表完整心理学词表覆盖率。心理学成为第六个专业目标；考试目标和已有类别位号保持不变。选中目标只优先对应的英文译词，不改变中文候选顺序。

运行时仅载入 89 行映射和 443 行标签，不扫描 11,085 行原始 CSV。固定数据、审校、SHA-256 与可重复构建记录见 [`naer-psychology-manifest.json`](../vocabulary/data/naer-psychology-manifest.json)、[`36-naer-psychology-reviewed.tsv`](../vocabulary/data/batches/36-naer-psychology-reviewed.tsv)、[`36-naer-psychology-tags-reviewed.tsv`](../vocabulary/data/batches/36-naer-psychology-tags-reviewed.tsv)、[署名说明](../vocabulary/data/NAER-PSYCHOLOGY-ATTRIBUTION.md)和[`build_naer_psychology_batch.py`](../scripts/build_naer_psychology_batch.py)。

本批更新共享词库与 Android、Windows、iOS 的目标设置源码，没有打包或安装客户端。电脑版仍按用户安排，等词汇批次完成后再处理。
