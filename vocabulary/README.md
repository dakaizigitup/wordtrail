# 英语考试标签与实际扩词

批次16使用固定 [FIBO 金融本体](https://github.com/edmcouncil/fibo) MIT 快照，为已有且拼音可达的英文词头补充商务/金融标签。批次17从固定 [Better Quant Wiki](https://github.com/Tomortec/better-quant-wiki) MIT 双语术语表新增7组经逐项审校的可达金融映射，其中3个是新英文词头。批次18从 [CFPB 2024 官方中英金融术语表](https://files.consumerfinance.gov/f/documents/cfpb_adult-fin-ed_chinese-style-guide-glossary.pdf) 筛出246组去重后可核验候选，映射率为223/246（90.65%）；接受67组映射（13个新英文词头），新增193个商务标签归属。批次19从固定 [finance_i18n](https://github.com/hotvulcan/finance_i18n) MIT 词表中审核491组本地可达候选，新增47组映射（12个新英文词头）和41个商务标签归属。批次20从固定 [computerese-cross-references](https://github.com/EarsEyesMouth/computerese-cross-references) MIT 快照过滤书籍脚注与长解释后，审核75组精确候选，增加13组既有英文词头的新中文义项（新英文词头0个）及55个计算机标签归属。批次21从美国国家医学图书馆 NLM MeSH 2026 英文主题词与本机拼音可达释义交集中，新增75组经审校的医学映射（74个新英文词头）和1,079个医学标签成员；256组候选中7组排除、174组暂缓。批次22从 Wikidata CC0 中文标签与 MeSH P486 编号交集中复核48组可输入候选，新增25组医学译词（24个此前未映射词头）和24个医学标签成员。批次23扩展到1,326个有本地音标及名词词性证据的 MeSH 编号，48组进入逐项审核，新增19组映射（18个此前未映射词头）和18个医学标签成员；3组排除、26组暂缓。批次26–27从 NAER 生命科学和兽医学 OGL v1.0 数据中继续筛选，27 组候选逐项审核后接受13组映射（2个新英文词头）、排除14组，并增加4个医学标签成员。两个批次要求精确拼音、IPA、ECDICT 名词义和 MeSH 主题，保留逐项理由；来源及散列见 `data/NAER-LIFE-SCIENCE-ATTRIBUTION.md`、`data/NAER-VETERINARY-ATTRIBUTION.md`、`data/naer-life-science-manifest.json`、`data/naer-veterinary-manifest.json`、`data/batches/26-naer-life-science-reviewed.tsv` 和 `data/batches/27-naer-veterinary-reviewed.tsv`。两批 Wikidata 来源、许可、固定查询、实体修订和逐项决定见 `data/WIKIDATA-MEDICAL-ATTRIBUTION.md`、`data/wikidata-medical-manifest.json`、`data/wikidata-medical-manifest-2.json`、`data/batches/22-wikidata-medical-reviewed.tsv` 和 `data/batches/23-wikidata-medical-reviewed.tsv`。MeSH 提供英文概念与主题范围；批次21中文短义由 ECDICT MIT 精确核验，批次22–23的中文标签来自 Wikidata。批次18的90.65%只针对其拼音、音标和 ECDICT 均核验通过的筛选子集，不代表来源全表覆盖；金融、计算机和医学专业词汇没有固定完整分母，因此不宣称总体覆盖率。来源、许可边界、审校表和构建脚本见 `data/FIBO-ATTRIBUTION.md`、`data/BETTER-QUANT-ATTRIBUTION.md`、`data/CFPB-ATTRIBUTION.md`、`data/FINANCE-I18N-ATTRIBUTION.md`、`data/COMPUTERESE-ATTRIBUTION.md`、`data/MESH-ATTRIBUTION.md`、`data/WIKIDATA-MEDICAL-ATTRIBUTION.md`、`data/batches/19-finance-i18n-reviewed.tsv`、`data/batches/20-computerese-reviewed.tsv`、`data/batches/21-mesh-medical-reviewed.tsv`、`data/batches/22-wikidata-medical-reviewed.tsv` 和 `data/batches/23-wikidata-medical-reviewed.tsv`。

标签索引从 ECDICT（MIT）和 KyleBing/english-vocabulary（BSD-3-Clause）提取词条与六类考试收录关系，不复制其释义、例句、图片或音频。0.1.10 的独立扩词表额外从 ECDICT 提取短中文词义对应。English Wiktionary 派生数据单独按 CC BY-SA 4.0 署名和分发：早期22条英语考试映射分别在 `data/wiktionary-expansion.tsv` 与 `data/wiktionary-expansion-2.tsv`；批次14新增10条医学映射，并加入可单独选择的计算机、商务、医学标签。批次15从固定 CC BY-SA 4.0 计算机术语对照表新增26组可达对应，其中5个此前没有的英文词头。固定来源、逐项核对和许可边界见 `data/CJK-COMPSCI-ATTRIBUTION.md`、`data/batches/15-cjk-compsci-reviewed.tsv`、`data/batches/15-cjk-compsci-evidence.tsv`、`data/cjk-compsci-manifest.json` 与 `data/WIKTIONARY-ATTRIBUTION.md`。其他 CC-CEDICT、OpenEtymology、KOReader 等来源仍按各自许可独立保存，不混作同一词源。

`python scripts/prepare_vocabulary.py --download` 可在项目根目录重建；下载缓存放在忽略的 `build/vocabulary-research/`。已有研究缓存时无需 `--download`。输出逐字节确定；所有输入先校验 SHA-256。普通用户无需下载这些开发数据，程序嵌入精简索引。

词条保守归一化：首尾空白、Unicode 小写，完整词面精确匹配。保留短语、连字符、撇号，不按子串或词根猜标签。重复词求标签并集，并分别保存两个来源的位掩码。标签仅代表社区词表收录类别，不代表词义难度、个人水平或官方完整考试范围。

批次35固定 NAER Education Terminology（dataset 6319，Open Government Data License v1.0），经精确词义、IPA、拼音和容量筛选后纳入23组映射、2个新英文词头和130个教育来源成员。逐项审核、来源快照、SHA-256 与可重复构建见 `data/NAER-EDUCATION-ATTRIBUTION.md`、`data/naer-education-manifest.json`、`data/batches/35-naer-education-reviewed.tsv` 和 `scripts/build_naer_education_batch.py`。运行时仅载入紧凑 TSV，不扫描完整 CSV。

批次36固定 NAER Psychology Terminology（dataset 15167，Open Government Data License v1.0），逐项审校后纳入89组映射、14个新英文词头及443个心理学来源成员。逐项决定、来源快照、SHA-256 与可重复构建见 `data/NAER-PSYCHOLOGY-ATTRIBUTION.md`、`data/naer-psychology-manifest.json`、`data/batches/36-naer-psychology-reviewed.tsv` 和 `scripts/build_naer_psychology_batch.py`。运行时仅载入紧凑 TSV，不扫描完整 CSV。

0=四级、1=六级、2=专四、3=专八、4=托福、5=雅思、6=计算机、7=商务、8=医学、9=行政学、10=教育、11=心理学；新增领域位号追加在旧目标之后，旧设置位号保持不变。领域类别独立于考试类别。未选目标时保留原译词顺序；多选目标采用任一命中优先、组内稳定排序。中文候选保持原顺序，译词对应的读音、词性、熟悉度一起排序。输入界面不展示 A1–C2 标签。

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

## 专业词汇首批（批次14）

运行索引增加计算机、商务、医学三个独立标签；只有来源主题、完整译词、既有中文译词和本机真实拼音候选精确吻合时才贴标签。首批可触达标签覆盖149个计算机译词、100个商务译词、415个医学译词；这些是固定快照与现有候选面的社区数据统计，不表示官方专业课程覆盖率。另增加10组经人工复核的医学中文—英文映射。11条新词候选中排除1条可能造成误导的释义，不把“打标签”计作新增译词。

候选发现由 `python scripts/build_professional_vocabulary.py --candidates-only` 重建；研究队列只写入被 Git 忽略的 `build/source-audit/`。确认 `data/batches/14-professional-reviewed.tsv` 中每条候选都有 accept/reject 决定后，运行 `python scripts/build_professional_vocabulary.py --apply` 可确定性重建三份运行/审计数据与 SHA-256 清单。脚本校验固定 Kaikki 派生 Wiktionary 快照、ECDICT、拼音候选面、基线译词和英美音标，不联网下载或扫描研究文件作为运行时索引。

## 计算机术语第二段（批次15）

固定 `dahlia/cjk-compsci-terms` 提交 `3cf825e81375202fd408427933c3a30442defa4f` 的28份 YAML 表采用 CC BY-SA 4.0。运行数据只取简体中文键和本地真实拼音候选可达项；已有映射只有在组成对应完全匹配英文词面时才贴“计算机”标签。另逐项审校28个有本地英美音标和 ECDICT 词性依据的候选，接受26组、排除两组误配 `value → 变量/常量`。新增组中5个英文词头是此前词库没有的，其他是给已有英文词头补充准确的计算机中文入口。上游表、许可、输入/输出 SHA-256、审校结论和修改范围见 `data/CJK-COMPSCI-ATTRIBUTION.md`、`data/sources/cjk-compsci-terms/`、`data/batches/15-cjk-compsci-reviewed.tsv`、`data/batches/15-cjk-compsci-evidence.tsv` 与 `data/cjk-compsci-manifest.json`。

候选与运行数据通过 `python scripts/build_cjk_compsci_batch.py --discover` / `python scripts/build_cjk_compsci_batch.py` 复建。正常键盘查询只读编译进来的紧凑 TSV，不读取上游 YAML 表、审计记录或研究数据库。该批覆盖的是固定社区计算机术语表中可输入且有音标的子集，不表示完整专业课程覆盖率。

## 0.1.23 拼音可达率补充

批次11–12已添加2,291组专四、专八、托福、雅思考试映射。复核拼音可达率时发现，旧统计漏掉键盘实际支持的单字候选，也没有统计新拼音键同时解锁的原始词库和既有扩展释义；按实际候选面修正后，批次12托福拼音可达率为86.55%。批次13只为现有译词加拼音，不新增中英释义，加入407个频率为0的新键，将托福拼音可达率提升到90.01%。所有读音均来自固定 CC-CEDICT/Rime ICE 精确词条；两边都有记录时须完全一致，多音歧义、冲突和无法核验候选不加入。逐键记录、hash、重建命令和许可见 `data/EXAM-TARGETS-ATTRIBUTION.md` 与 `data/exam-target-batch-13-manifest.json`。

四级/六级/专四/专八/托福/雅思精确拼音可达率为97.74%、96.67%、96.15%、94.05%、90.01%、94.91%；其含义是完整中文词面存在本地拼音键，不代表译词显示在第一页。固定社区词表并非官方完整考纲。

批次24从國家教育研究院《醫學學術名詞》固定开放数据快照中审查154组新词头对应，接受57组、排除12组、暂缓85组，并新增57个医学标签成员。每个采纳的英语词头有本地音标和 ECDICT 名词词性证据；繁体中文转换为本地拼音可达的简体形式。来源逐行网址字段为 `[url]` 占位值，因此不推断整份资料集的医学覆盖率。运行时只加入57行映射和57行标签。来源与许可见 `data/NAER-MEDICAL-ATTRIBUTION.md`，审校见 `data/batches/24-naer-medical-reviewed.tsv`。

批次25继续从同一来源的已有词头中筛选，使用 MeSH 主题和 ECDICT 完整名词义交叉核对45组候选，接受37组中英映射（0个新英文词头），新增18个医学标签成员。运行时只加入37行映射和18行标签；每条精确释义和来源证据见 `data/batches/25-naer-medical-existing-headwords-reviewed.tsv` 与 `data/naer-medical-manifest-2.json`。

## 批次28：WordLevel TOEFL/IELTS 学术词表

固定 [WordLevel GitHub 数据集](https://github.com/gungorkaya-eng/toefl-essential-vocabulary-dataset)提交 `85d4392a2254d2a1ad73cf12cdd8898b49cd3295`。1,000个来源词中，946个已有本地中文释义和音标并加入 TOEFL/IELTS 双标签；新增122个 TOEFL、254个 IELTS 标签归属（重叠），81个词头首次同时获得两类标签。另逐项审核11条可输入候选，接受4组中英对应（3个新英文词头）、排除6组、暂缓1组；54个来源词尚无可用本地映射/音标。词表为社区学术词表，不代表官方考试范围。GitHub 仓库声明 MIT，Mendeley DOI 记录声明 CC BY 4.0；本项目同时保留 MIT 文本、作者署名和 [WordLevel 链接](https://wordlevel.net)。固定数据、许可元数据、SHA-256、构建脚本及逐词处理见 `data/WORDLEVEL-ATTRIBUTION.md`、`data/wordlevel-toefl-ielts-manifest.json`、`data/batches/28-wordlevel-reviewed.tsv`、`data/batches/28-wordlevel-tag-evidence.tsv` 和 `../scripts/build_wordlevel_toefl_batch.py`。
