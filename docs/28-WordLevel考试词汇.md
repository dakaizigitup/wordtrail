# WordLevel TOEFL/IELTS 学术词汇（批次28）

本批固定 [WordLevel TOEFL Essential Vocabulary Dataset](https://github.com/gungorkaya-eng/toefl-essential-vocabulary-dataset) 的 1,000 词 CSV，版本为提交 `85d4392a2254d2a1ad73cf12cdd8898b49cd3295`。GitHub README 将其描述为 TOEFL iBT、IELTS 和学术英语词表；这是社区整理的学习词表，不是官方考纲。我们只使用它证明词表收录关系，不把其 AI 生成/整理的英文释义、例句或同义词装进输入法。

对照现有共享词库后，批次29完成时有 944 个词头同时具备中文释义和本地音标。经逐项审校的 ECDICT 补充新增 4 组中英对应、3 个此前没有映射的英文词头：`aberration → 畸变`、`curricula → 课程`、`enshroud → 掩盖 / 隐蔽`。已有的 `gestation → 妊娠` 不重复计数。另有 6 条候选因中文义项不匹配而排除；`eminently → 非常` 虽然义项正确，但对应拼音键已达到每键 8 条扩词上限，因此暂缓。

最终有 947/1,000 个来源词头同时具备本地中文释义和音标，纳入 TOEFL、IELTS 两个可选标签。新增 123 个 TOEFL 标签归属和 255 个 IELTS 标签归属；类别有交集，其中 82 个词头首次同时获得这两个标签。剩余 53 个来源词没有同时满足本地映射与音标条件，未进入本批运行索引。来源词表不是官方清单，因此 94.7% 只描述与此固定社区词表的本地可用重叠，不代表 TOEFL 或 IELTS 的完整覆盖率。

上游 GitHub 仓库声明 MIT，随源码保留其许可文件；[对应 Mendeley Data 记录](https://data.mendeley.com/datasets/wfksk94zr9/1)声明 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。两个来源的许可元数据不同，所以本项目同时保留 MIT 许可文本、CC BY 署名信息，并按上游要求链接到 [WordLevel](https://wordlevel.net)。新增295个来源词头的至少一个考试归属，其中81个同时新增 TOEFL 和 IELTS 归属。固定源文件、输入输出 SHA-256、标签逐词理由及可重复构建命令见 [署名说明](../vocabulary/data/WORDLEVEL-ATTRIBUTION.md)、[`wordlevel-toefl-ielts-manifest.json`](../vocabulary/data/wordlevel-toefl-ielts-manifest.json)、[`28-wordlevel-reviewed.tsv`](../vocabulary/data/batches/28-wordlevel-reviewed.tsv)、[`28-wordlevel-tag-evidence.tsv`](../vocabulary/data/batches/28-wordlevel-tag-evidence.tsv) 和 [`build_wordlevel_toefl_batch.py`](../scripts/build_wordlevel_toefl_batch.py)。

源词表还把固定短语 `inasmuch as` 错并成单词 `inasmuchas`；该项已从映射候选和运行标签中排除。这也说明这份社区列表不能当作已权威校订的官方清单。

验证：固定输入重建检查通过；整个 Rust 工作区 Windows GNU 目标测试 **48/48 通过**，其中词库模块 32/32，覆盖新增标签来源、四组映射、排除/暂缓项和目标优先顺序。运行时只增加精简 TSV，不扫描原始 CSV；未在本批构建安装包。译词优先级只作用于英文译词，中文候选顺序保持不变。Windows 电脑版尚未打包或安装。
