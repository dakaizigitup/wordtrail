# OpenEtymology CET4/CET6 补词（批次29）

本批固定 [openetymology/OpenEtymology](https://github.com/openetymology/OpenEtymology) 提交 `7d89f3697abf26e305fe2627f181b692c2c10b28` 的 CET4 与 CET6 词单。上游 `DATA_LICENSE.md` 将公开单词表声明为 CC BY-SA 4.0；项目只提取规范化英文词头与名单成员关系，不复制词源、例句或释义。固定原文件 SHA-256 和许可证文本见 [`openetymology-cet-tags-manifest.json`](../vocabulary/data/openetymology-cet-tags-manifest.json) 及[署名说明](../vocabulary/data/OPENETYMOLOGY-CET-DATA-ATTRIBUTION.md)。

| 参考词单 | 词头数 | 加入本来源标签、原 ECDICT/KyleBing 尚无对应标签 | 本地已有映射 | 拼音可达映射 |
| --- | ---: | ---: | ---: | ---: |
| CET4 | 4,533 | 247 | 4,503（99.34%） | 4,411（97.31%） |
| CET6 | 2,219 | 2 | 2,207（99.46%） | 2,177（98.11%） |

这些是 OpenEtymology 两份固定社区词单的统计，不是官方考纲覆盖率。映射覆盖只要求至少有一组本地英文释义；拼音可达要求其中一条中文释义能由本地拼音输入。低频释义仍可能排在候选后面。

把本批两份名单与此前固定的考试来源合并后，当前六类目标覆盖如下。计数按去重英文词头计算，拼音可达计入随包拼音 overlay；不同名单可以重叠。

| 目标 | 映射覆盖 | 拼音可达 |
| --- | ---: | ---: |
| 四级 | 98.67% | 97.69% |
| 六级 | 97.65% | 96.69% |
| 专四 | 97.56% | 96.15% |
| 专八 | 95.85% | 94.05% |
| 托福 | 90.89% | 90.05% |
| 雅思 | 96.33% | 95.02% |

该合并口径是 ECDICT/KyleBing、OpenEtymology 和 WordLevel 等固定社区来源的并集，不代表官方完整考纲或考试成绩。

两个词单中有45个英文词头此前没有中文映射。把固定拼音 overlay 也纳入键面后，9组候选同时具备 ECDICT 完整短义、本地 IPA、可直接拼音输入的中文键和词条容量；6组经逐条审核接受，覆盖4个新英文词头：

| 中文输入 | 新增英文译词 | 词性 |
| --- | --- | --- |
| 玷辱 | dishonor | v. |
| 不名誉 | dishonor | n. |
| 永久 | permanently | adv. |
| 充分、足够 | sufficiently | adv. |
| 附加 | tack | v. |

另外2组排除，1组暂缓：`不变/持久 → permanently` 不是自然的副词译法；`食物 → tack` 虽是 ECDICT 收录的罕见名词义，但来源只有词头、没有语境，故暂缓。9组候选和理由全部保留在 [`29-openetymology-cet-reviewed.tsv`](../vocabulary/data/batches/29-openetymology-cet-reviewed.tsv)。

新增名单索引为5,709个去重词头、约55 KB；扩词索引为6行、196字节。查询时只把这些行与既有索引合并加载一次，不扫描上游词单，也不改变中文候选顺序。拼音候选、词汇标签、译词优先顺序和英语音标均由本地现有索引提供。

复建和验证：

```powershell
py scripts/build_openetymology_cet_tags.py --check
py scripts/build_openetymology_cet_batch.py --check
```

OpenEtymology 词单为 CC BY-SA 4.0；新增中文短义来自 ECDICT MIT。该来源及其适配名单按 CC BY-SA 4.0 保留署名与相同方式共享信息。
