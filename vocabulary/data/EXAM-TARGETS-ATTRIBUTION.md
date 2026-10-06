# 专四、专八、托福、雅思词汇补充来源

本批只从现有拼音候选与青简英语释义中筛出能直接输入的完整中文短义；每个新增英文词最多增加一条中文键。词条须有专四、专八、托福或雅思社区词表标签、随包英式/美式 IPA、与现有中文键相同的词性，并且不突破每键八条扩词上限。构建规则、逐词选入记录和来源散列见 [`batches/09-exam-target-reviewed.tsv`](batches/09-exam-target-reviewed.tsv)、[`batches/09-exam-target-candidate-summary.json`](batches/09-exam-target-candidate-summary.json) 及 [`exam-target-manifest.json`](exam-target-manifest.json)。候选筛查表保存在 [`batches/09-exam-target-candidate-review.tsv`](batches/09-exam-target-candidate-review.tsv)。

## ECDICT 派生条目

署名：Skywind3000 与 ECDICT contributors。来源：[skywind3000/ECDICT](https://github.com/skywind3000/ECDICT)，固定提交 `bc015ed2e24a7abef49fc6dbbb7fe32c1dadaf8b`，数据文件 `ecdict.csv`，SHA-256 `1a6947e04785db63613a92e14903cdae7954f7e84860b10e68e5c7cbb3f9c3cf`。许可为 [MIT](https://github.com/skywind3000/ECDICT/blob/bc015ed2e24a7abef49fc6dbbb7fe32c1dadaf8b/LICENSE)，完整许可随包见 `ECDICT-LICENSE`。

从词典的完整词性标注中文释义中提取与本机拼音候选精确相同的短词义；筛选缺少运行时映射且带考试标签的英文词，要求现有青简释义具有同词性。运行时数据保存在 `exam-target-ecdict-expansion.tsv`。词库只保存“中文键—英文词—词性”对应，不复制例句、音频或完整释义。

## KyleBing 派生条目

署名：KyleBing 与贡献者。来源：[KyleBing/english-vocabulary](https://github.com/KyleBing/english-vocabulary)，固定提交 `c4c6c80879ff17d7025c28fb853a4991c8e6be6a`。仅使用专四、专八、托福、雅思正序简单词表中带词性的完整中文义项；许可为 [BSD 3-Clause](https://github.com/KyleBing/english-vocabulary/blob/c4c6c80879ff17d7025c28fb853a4991c8e6be6a/LICENSE)，完整许可随包见 `KyleBing-LICENSE`。

只收录未能从 ECDICT 的同词、同中文键、同词性释义中找到匹配的词条，并仍要求精确拼音候选、随包 IPA、现有中文键及词性兼容。运行时数据独立保存在 `exam-target-kylebing-expansion.tsv`。

这两份运行文件按各自来源分别署名和保留许可，不合并许可。考试类别是固定社区词表的成员关系，不等于官方完整考纲；覆盖率统计见本批清单。

## 专八、托福、雅思补充批次（batch 11）

本批从多种固定词典中提取完整短义；要求考试标签、随包 IPA、词性和拼音来源可核对，并将不同许可证来源分开保存。逐项证据、自动筛选限制及 SHA-256 均见 [`batches/11-exam-target-reviewed.tsv`](batches/11-exam-target-reviewed.tsv) 和 [`exam-target-batch-11-manifest.json`](exam-target-batch-11-manifest.json)。本批按规则筛选，未逐条人工校阅。

- **ECDICT MIT** 与 **KyleBing BSD-3-Clause**：分别置于 `exam-target-batch-11-ecdict-expansion.tsv`、`exam-target-batch-11-kylebing-expansion.tsv`；共同匹配的条目单独置于 `exam-target-batch-11-dual-expansion.tsv`。许可全文见上文及 `ECDICT-LICENSE`、`KyleBing-LICENSE`。
- **Chinese Open Wordnet**：采用 `omwn/omw-data` 固定提交 `406bf83b3c507a3d1f26e88252d5d66893fd36bf` 的 COW `wns/cow/wn-data-cmn.tab`（SHA-256 `379fd2e41d3e1395f9f27cf23a39c6181849ffb4020c14a07ed2a4d4dd651122`）。COW 许可要求在所有副本保留著作权声明与免责声明，全文见 [`CHINESE-OPEN-WORDNET-LICENSE.txt`](CHINESE-OPEN-WORDNET-LICENSE.txt)。仅 COW 依据的映射独立保存在 `exam-target-batch-11-cow-expansion.tsv`。
- **KOReader 英中词典**：署名 KOReader Dictionaries contributors，固定发布版 v1.2.0，来源 [DanielGregorini/koreader-dicts](https://github.com/DanielGregorini/koreader-dicts/releases/tag/v1.2.0)，下载文件 SHA-256 `910d8fc3bf054f7a36f5db134f0624619711e5b414ebf7de45a3c0e04e98232c`。其编译版采用 CC BY-SA 4.0，且各底层词库的许可仍各自适用；随包保留上游 [`KOReader-ATTRIBUTION.txt`](KOReader-ATTRIBUTION.txt) 和 [`KOReader-LICENSE.txt`](KOReader-LICENSE.txt)。运行数据区分 `exam-target-batch-11-cc-by-sa-expansion.tsv`（CC BY-SA 来源）与 `exam-target-batch-11-koreader-cow-expansion.tsv`（同时含 KOReader 编译词典及 COW 义项证据），避免把两类来源混为一个许可。
- **FMLD**：采用 [jiong3/fmld](https://github.com/jiong3/fmld) 固定提交 `de1a3c543fb35ede7f46e335d12f28572578c2b6`（输入 SHA-256 `adffa622f223b33b03e76fd1d8f7c57cd90f6491cd5e9cec69a984ec1b3bc1ad`），来源许可 CC BY-SA 4.0。只提取完整英文整词释义与词性一致的短条，进入 `exam-target-batch-11-cc-by-sa-expansion.tsv`。
- **CC-CEDICT**：沿用上文已说明的 2026-06 固定镜像及 CC BY-SA 4.0 许可。此处只接受完整英文词头对完整中文释义的匹配，词性从固定 ECDICT 核对；进入独立 CC BY-SA 文件。
- 拼音覆盖单独存于 `pinyin-overlays/exam-target-batch-11.tsv`。每行注明 CC-CEDICT 或 Rime ICE 来源；Rime ICE 固定提交和字典文件散列见后续 batch 12 清单，完整 GPL-3.0 许可随包见 [`RIME-ICE-LICENSE.txt`](RIME-ICE-LICENSE.txt)。该补充拼音频率为 0，只追加到新中文键，不调整青简原有候选顺序。

本批新增 1,592 组、1,592 个此前未映射词及 411 个新拼音键。六类社区考试词表可有交集；分来源数量和映射/拼音可触达口径以机器清单为准。

## ECDICT 与拼音键补充批次（batch 12）

本批新增 699 组 ECDICT MIT 词义映射，其中专四 64、专八 308、托福 438、雅思 112（类别交叉）；同时保留四级、六级成员标签。每条来自固定 ECDICT 的完整、带词性中文短义；只给原数据中缺少拼音键的中文词补拼音。旧青简拼音键优先；新键来自已固定的 CC-CEDICT 或 Rime ICE 数据，两边均有读音记录时要求归一化后完全一致。新键频率为 0，原词库文件不改写，原候选顺序保持不变。

运行映射为 [`exam-target-batch-12-ecdict-expansion.tsv`](exam-target-batch-12-ecdict-expansion.tsv)，逐词审计与来源行号为 [`batches/12-ecdict-new-pinyin-reviewed.tsv`](batches/12-ecdict-new-pinyin-reviewed.tsv)，新增拼音及逐行来源在 [`pinyin-overlays/exam-target-batch-12.tsv`](pinyin-overlays/exam-target-batch-12.tsv)，重建规则和 SHA-256 见 [`exam-target-batch-12-manifest.json`](exam-target-batch-12-manifest.json)。ECDICT 词义数据按 MIT 许可，拼音键保留其逐行上游许可来源。

batch 11 与 batch 12 合并后，专四/专八/托福/雅思的映射覆盖率为 **97.56% / 95.85% / 90.81% / 96.20%**。旧版可达率统计只覆盖2–6字词面，漏掉键盘实际支持的单字候选，也没有计入新拼音键同时解锁的原始词库释义和其他既有扩词。按实际运行候选面修正后，六类四级/六级/专四/专八/托福/雅思的拼音可达率为 **95.62% / 94.38% / 94.35% / 92.19% / 86.55% / 92.68%**。映射覆盖与可达率是两项独立统计；全部数字基于本项目固定社区词表，不代表官方完整考纲，也不保证对应译词总在候选第一页。

## 拼音可达率补充（batch 13）

batch 13 不增加英语释义，只为已存在的考试词义补充407个频率为0的拼音键。精确词条读音全部来自 CC-CEDICT 和/或 Rime ICE 固定数据：1个仅有 CC-CEDICT 记录、244个仅有 Rime ICE 记录，162个在两边都有记录且归一化读音完全一致。无法唯一核验、存在歧义或来源冲突的键不纳入。

所有实际选入读音均写在 [`pinyin-overlays/exam-target-batch-13.tsv`](pinyin-overlays/exam-target-batch-13.tsv)，逐项筛选理由和示例释义见 [`batches/13-exam-pinyin-reachability.tsv`](batches/13-exam-pinyin-reachability.tsv)，确定性选择脚本为 [`select_exam_target_batch_13.py`](../../scripts/select_exam_target_batch_13.py)，数量、输入/输出散列和来源清单见 [`exam-target-batch-13-manifest.json`](exam-target-batch-13-manifest.json)。歧义读音、来源相互冲突、或无法由 pinned 来源唯一验证的词面不纳入。

batch 13 后四级/六级/专四/专八/托福/雅思拼音可达率分别为 **97.74% / 96.67% / 96.15% / 94.05% / 90.01% / 94.91%**。中文候选顺序保持不变；托福达到本批设定的90%目标。覆盖率仍基于社区词表，不代表官方完整考纲。
