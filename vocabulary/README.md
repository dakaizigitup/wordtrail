# 英语考试标签与实际扩词

仅提取 ECDICT（MIT）和 KyleBing/english-vocabulary（BSD-3-Clause）的词条与六类收录标签。标签索引未复制释义、例句、图片或音频。0.1.10 的独立扩词表额外从 ECDICT 提取短中文词义对应，不复制例句或音频。许可全文与固定提交、输入文件 SHA-256、分类数量见 `data/`。

`python scripts/prepare_vocabulary.py --download` 可在项目根目录重建；下载缓存放在忽略的 `build/vocabulary-research/`。已有研究缓存时无需 `--download`。输出逐字节确定；所有输入先校验 SHA-256。普通用户无需下载这些开发数据，程序嵌入精简索引。

词条保守归一化：首尾空白、Unicode 小写，完整词面精确匹配。保留短语、连字符、撇号，不按子串或词根猜标签。重复词求标签并集，并分别保存两个来源的位掩码。标签仅代表社区词表收录类别，不代表词义难度、个人水平或官方完整考试范围。

0=四级、1=六级、2=专四、3=专八、4=托福、5=雅思；类别 ID 与位号稳定。未选目标时保留原译词顺序；多选目标采用任一命中优先、组内稳定排序。中文候选保持原顺序，译词对应的读音、词性、熟悉度一起排序。原有 CEFR 数据单独保留。

来源：

- https://github.com/skywind3000/ECDICT/tree/bc015ed2e24a7abef49fc6dbbb7fe32c1dadaf8b
- https://github.com/KyleBing/english-vocabulary/tree/c4c6c80879ff17d7025c28fb853a4991c8e6be6a

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
