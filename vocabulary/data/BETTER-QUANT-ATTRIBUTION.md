# Better Quant Wiki 署名与数据说明

- 上游：Tomortec，[Better Quant Wiki](https://github.com/Tomortec/better-quant-wiki)
- 固定提交：`5611485adb669828fcaf704aeb2ce9c8a86886d4`
- 许可：MIT；许可原文随包保存在 `vocabulary/data/sources/better-quant-wiki/LICENSE`
- 固定来源快照、文件 SHA-256 和汇总散列：`better-quant-manifest.json`

本项目从该版本的双语量化金融术语表中筛选出 211 个词条；其中 41 个中文词面能由本机拼音候选直接触达。经逐项检查后，运行时新增 7 组中英映射和 7 条商务标签记录，覆盖 6 个新增商务标签成员；3 个英文词头此前未在运行扩展中出现。另有 34 个候选未纳入，决定及原因保存在 `batches/17-better-quant-reviewed.tsv`，完整发现记录保存在 `batches/17-better-quant-candidates.tsv`。

选入词条为：

| 中文 | 英文 | 上游词条 |
|---|---|---|
| 市值 | capitalization | [capitalization](https://wiki.zibenxiuxing.com/glossary/capitalization) |
| 复利 | compounding | [compounding](https://wiki.zibenxiuxing.com/glossary/compounding) |
| 回撤 | drawdown | [drawdown](https://wiki.zibenxiuxing.com/glossary/drawdown) |
| 权益 | equity | [equity](https://wiki.zibenxiuxing.com/glossary/equity) |
| 杠杆 | leverage | [leverage](https://wiki.zibenxiuxing.com/glossary/leverage) |
| 报价 | quotation | [quotation](https://wiki.zibenxiuxing.com/glossary/quotation) |
| 证券 | security | [security](https://wiki.zibenxiuxing.com/glossary/security) |

本项目作了修改：只保留上述可由现有拼音输入的精简中英词条，并为英文词头增加商务/金融来源标签；没有复制上游释义、定义、例句或网页内容到运行词库。英语音标沿用本项目已有的独立音标库；缺少 UK 或 US 读音的一侧继续留空，不补猜。原有中文候选顺序和译词不变。

重建命令：`python scripts/build_quant_finance_batch.py`。运行时索引只读取 `better-quant-expansion.tsv` 和 `better-quant-business-tags.tsv`；上游快照及审校材料不参与按键查询。
