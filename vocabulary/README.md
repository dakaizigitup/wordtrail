# 英语考试标签与实际扩词

仅提取 ECDICT（MIT）和 KyleBing/english-vocabulary（BSD-3-Clause）的词条与六类收录标签。标签索引未复制释义、例句、图片或音频。0.1.10 的独立扩词表额外从 ECDICT 提取短中文词义对应，不复制例句或音频。English Wiktionary 派生数据单独按 CC BY-SA 4.0 署名和分发：首批15条在 `data/wiktionary-expansion.tsv`，第二批7条在 `data/wiktionary-expansion-2.tsv`，逐词固定修订见 `data/batches/03-wiktionary-reviewed.tsv` 与 `data/batches/06-wiktionary-zh-reviewed.tsv`，累计数量、来源快照及许可边界见两份 `wiktionary-manifest*.json` 和 `data/WIKTIONARY-ATTRIBUTION.md`。0.1.15 首段和0.1.16第二段分别加入58、66条 CC-CEDICT 派生对应，独立放在 `data/cccedict-expansion.tsv` 与 `data/cccedict-expansion-2.tsv`；逐批署名、审校记录和快照校验见 `data/CC-CEDICT-ATTRIBUTION.md`、两份 `cccedict-manifest*.json` 与 `data/batches/04-`、`05-cc-cedict-reviewed.tsv`。这些来源保持分开，不能把它们统称为同一种许可。

`python scripts/prepare_vocabulary.py --download` 可在项目根目录重建；下载缓存放在忽略的 `build/vocabulary-research/`。已有研究缓存时无需 `--download`。输出逐字节确定；所有输入先校验 SHA-256。普通用户无需下载这些开发数据，程序嵌入精简索引。

词条保守归一化：首尾空白、Unicode 小写，完整词面精确匹配。保留短语、连字符、撇号，不按子串或词根猜标签。重复词求标签并集，并分别保存两个来源的位掩码。标签仅代表社区词表收录类别，不代表词义难度、个人水平或官方完整考试范围。

0=四级、1=六级、2=专四、3=专八、4=托福、5=雅思；类别 ID 与位号稳定。未选目标时保留原译词顺序；多选目标采用任一命中优先、组内稳定排序。中文候选保持原顺序，译词对应的读音、词性、熟悉度一起排序。原有 CEFR 数据单独保留。

来源：

- https://github.com/skywind3000/ECDICT/tree/bc015ed2e24a7abef49fc6dbbb7fe32c1dadaf8b
- https://github.com/KyleBing/english-vocabulary/tree/c4c6c80879ff17d7025c28fb853a4991c8e6be6a
- CC-CEDICT：固定2026-06快照镜像与修订，见 data/CC-CEDICT-ATTRIBUTION.md 和 data/cccedict-manifest.json。

## 重建实际扩词

构建直接嵌入已经校验的 `data/english-expansion.tsv`，普通构建无需下载研究词典。
重新生成时先恢复发行数据，并执行（Windows 先加载 `scripts/env_native.ps1`）：

```powershell
python scripts/apply_upstream.py
python scripts/prepare_vocabulary.py --download
cargo run --offline -p wordtrail-mobile --bin export_glossary -- data/glossary-en.qj vendor/qingjian/assets/glossary/glossary-en.tsv build/expansion-base.tsv
python scripts/prepare_expansion.py --download
```

从实际打包释义导出基线，按精确中文词面、词性匹配补充；自动添加还需 WordNet 3.0 同义集合或形容词 similar-to 关系验证。词性、拼写、来源均随对应记录保留。人工补充映射单独在 `reviewed-expansion.tsv`，并拒绝已发现的歧义对（如 丰富→affluent）。同义校验不能消除所有多义词歧义；这批不是完整人工审校词典。

原释义不删不覆盖，每个中文词最多补充 8 条；原上游 `Translation::new` 仍限两条，兼容补丁提供独立 `Translation::expanded` 入口（总量限 12）。移动候选只显示第一条，详情显示全部；Windows 显示前两条并可轮换。未显示的额外译词不计入熟悉度曝光。个人译者学习/落盘仍委托原译者。

当前新增 1,595 组对应、1,307 个中文词条、1,539 个英文词；其中 615 个英文词在原全表不存在。六类数量是对应组的收录次数，不能相加作为去重词数。统计、所有固定输入 SHA-256 与数据输出校验见 `data/expansion-manifest.json`。WordNet 仅在构建时使用，不把其定义或整个词典装入运行时。许可及来源见 `data/WordNet-LICENSE`、`data/wordnet-source.json`。

兼容补丁应用前先逐文件核验原始/已补丁 SHA-256，遇到未识别修改停止，避免覆盖维护者改动。`python scripts/apply_upstream.py --restore` 可恢复管理过的修改；后续构建会再应用。完整源码 ZIP 包含已应用的文件及补丁清单，Git 保持固定上游提交不变。

## 批次01–02与后续重建

批次01生成数据来自 `python scripts/prepare_cet_batch.py`，批次02使用 `python scripts/prepare_candidate_batch.py --apply`，通过真实拼音词库导出的候选面审计新增项。`02-evidence.tsv` 记录588组双来源同义项、精确拼音键面、词频和每组处置理由；其322组中文释义无法由现有拼音输入，36组关系证据不足，230组通过规则或逐项人工复核。批次00/01/02 的输入、新增差异、证据和缺口原因分别留在 `data/batches/` 下对应批次文件。`prepare_expansion.py` 是批次00历史重建工具，运行前要注意它会重建旧扩词。

Wiktionary 小批筛查脚本 `python scripts/audit_wiktionary_cet_gaps.py` 将候选页缓存到被 Git 忽略的 `build/source-audit/`；它只用于研究，不会把抓取页直接交给运行时。人工确认项写入 `data/batches/03-wiktionary-reviewed.tsv`。运行 `python scripts/build_wiktionary_expansion.py` 可逐字节检查独立授权数据；明确要重新生成时使用 `--apply`。构建器要求逐条具备固定修订链接、四六级标签、相符词性、精确拼音候选和随包音标，并检查每个中文候选键的条数上限。

CC-CEDICT 候选由 `python scripts/audit_cedict_cet_gaps.py` 从固定、校验哈希的快照筛出；首段人工核对结果在 `data/batches/04-cc-cedict-review-input.tsv`，低频第二段在 `data/batches/05-cc-cedict-review-input.tsv`。`python scripts/build_cedict_expansion.py` 可校验所有来源行、整词释义、ECDICT 词性、考试标签、拼音键、音标与每键上限。默认确定性检查首段；第二段构建时显式传入 `--input`、`--reviewed-output`、`--runtime-output`、`--manifest-output`、`--batch-name 02-cc-cedict-2 --minimum-frequency 0 --prior-runtime vocabulary/data/cccedict-expansion.tsv`。使用 `--apply` 才会写入 CC BY-SA 4.0 的逐批审校表、运行 TSV 和清单。研究用原始快照与候选 TSV 保存在被忽略的 `build/source-audit/`，不进入运行包。

完整数据重建顺序（研究缓存已经准备且 SHA-256 校验通过）：

```powershell
python scripts/prepare_cet_batch.py
cargo run --locked --offline -p wordtrail-mobile --bin export_glossary -- data/glossary-en.qj vendor/qingjian/assets/glossary/glossary-en.tsv build/expansion-base.tsv
cargo run --locked --offline -p wordtrail-mobile --bin export_pinyin_candidates -- data/dict.qj build/pinyin-candidates.tsv
python scripts/prepare_candidate_batch.py --apply
python scripts/prepare_candidate_batch.py --apply --check
python scripts/build_cedict_expansion.py
python scripts/build_cedict_expansion.py --input vocabulary/data/batches/05-cc-cedict-review-input.tsv --reviewed-output vocabulary/data/batches/05-cc-cedict-reviewed.tsv --runtime-output vocabulary/data/cccedict-expansion-2.tsv --manifest-output vocabulary/data/cccedict-manifest-2.json --batch-name 02-cc-cedict-2 --minimum-frequency 0 --prior-runtime vocabulary/data/cccedict-expansion.tsv
```

`native/src/bin/export_pinyin_candidates.rs` 从固定 `data/dict.qj` 导出唯一拼音候选面；输入和输出哈希记录在批次02清单。自动新增要求固定四六级词表与 ECDICT 的完整短义和词性一致、拼音词库含有精确中文候选、原释义词性兼容且 WordNet 校验通过。人工核对项仍要求双来源同词同义同词性及精确候选面，可处理中文原词性差异和 WordNet 关系漏检。新中文键、短语和不可触达释义留待后续核对；不从子串猜测。

更新至0.1.16后累计扩词3,997组中英对应；其中3,858组在原 MIT/BSD 文件，15组 Wiktionary 派生和124组 CC-CEDICT 派生数据各自独立存放。批次02第二段新增后，四级映射覆盖率96.04%、六级92.91%，按精确拼音候选计算的可触达率分别为92.42%和88.68%，剩余512个去重四六级词未映射。六类考试数量是收录次数，不能相加作为去重词数；各来源清单与构建校验见 `data/expansion-manifest.json`、`data/wiktionary-manifest.json` 和两份 `data/cccedict-manifest*.json`。

覆盖率按完整英文词面统计；“可由候选触达”另按完整拼音候选导出表中的精确中文键统计，包括一字候选。0.1.13旧短义审计只统计2–6字中文释义，故其90.66%/86.46%不可直接与0.1.14完整键面口径相减。两项指标都不代表官方完整考纲。见 [分批计划](../docs/分批补词计划.md)、[0.1.11结果](../docs/0.1.11四六级补词.md)、[0.1.12结果](../docs/0.1.12四六级补词.md)、[0.1.13结果](../docs/0.1.13四六级补词.md) 与 [0.1.14结果](../docs/0.1.14四六级补词.md)。

0.1.20 起另有专四、专八、托福、雅思派生数据，ECDICT 与 KyleBing 来源分文件保留许可。覆盖率和精确拼音可触达率分别记录；此批由固定来源交叉筛选，未逐条人工审校。选入记录、数据散列、选择规则和复建命令见 [`09-exam-target-reviewed.tsv`](data/batches/09-exam-target-reviewed.tsv)、[`exam-target-manifest.json`](data/exam-target-manifest.json) 与 [`来源说明`](data/EXAM-TARGETS-ATTRIBUTION.md)。

## 0.1.23 拼音可达率补充

批次11–12已添加2,291组专四、专八、托福、雅思考试映射。复核拼音可达率时发现，旧统计漏掉键盘实际支持的单字候选，也没有统计新拼音键同时解锁的原始词库和既有扩展释义；按实际候选面修正后，批次12托福拼音可达率为86.55%。批次13只为现有译词加拼音，不新增中英释义，加入407个频率为0的新键，将托福拼音可达率提升到90.01%。所有读音均来自固定 CC-CEDICT/Rime ICE 精确词条；两边都有记录时须完全一致，多音歧义、冲突和无法核验候选不加入。逐键记录、hash、重建命令和许可见 `data/EXAM-TARGETS-ATTRIBUTION.md` 与 `data/exam-target-batch-13-manifest.json`。

四级/六级/专四/专八/托福/雅思精确拼音可达率为97.74%、96.67%、96.15%、94.05%、90.01%、94.91%；其含义是完整中文词面存在本地拼音键，不代表译词显示在第一页。固定社区词表并非官方完整考纲。
