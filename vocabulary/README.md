# 英语考试标签

仅提取 ECDICT（MIT）和 KyleBing/english-vocabulary（BSD-3-Clause）的词条与六类收录标签。未复制源项目释义、例句、图片或音频。许可全文与固定提交、输入文件 SHA-256、分类数量见 `data/`。

`python scripts/prepare_vocabulary.py --download` 可在项目根目录重建；下载缓存放在忽略的 `build/vocabulary-research/`。已有研究缓存时无需 `--download`。输出逐字节确定；所有输入先校验 SHA-256。普通用户无需下载这些开发数据，程序嵌入精简索引。

词条保守归一化：首尾空白、Unicode 小写，完整词面精确匹配。保留短语、连字符、撇号，不按子串或词根猜标签。重复词求标签并集，并分别保存两个来源的位掩码。标签仅代表社区词表收录类别，不代表词义难度、个人水平或官方完整考试范围。

0=四级、1=六级、2=专四、3=专八、4=托福、5=雅思；类别 ID 与位号稳定。未选目标时保留原译词顺序；多选目标采用任一命中优先、组内稳定排序。中文候选保持原顺序，译词对应的读音、词性、熟悉度一起排序。原有 CEFR 数据单独保留。

来源：

- https://github.com/skywind3000/ECDICT/tree/bc015ed2e24a7abef49fc6dbbb7fe32c1dadaf8b
- https://github.com/KyleBing/english-vocabulary/tree/c4c6c80879ff17d7025c28fb853a4991c8e6be6a
