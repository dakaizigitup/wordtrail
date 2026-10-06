# CC-CEDICT 数据署名与许可

本批中文—英文对应改编自 CC-CEDICT，由 **MDBG 与 CC-CEDICT contributors** 提供。官方词典下载页及来源说明：[CC-CEDICT Editor](https://cc-cedict.org/editor/editor.php?handler=Download)。所选内容按 [Creative Commons Attribution-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-sa/4.0/)（CC BY-SA 4.0）提供。

用于筛查的固定快照是 2026 年 6 月 CC-CEDICT 文本，在 [TeaPearce/chinese-english-dictionary](https://github.com/TeaPearce/chinese-english-dictionary) 的固定提交 `a9aea223269eb9820590e5bca783eb299c317439` 中镜像：`data/cedict_ts_june2026.u8`。原始文件 SHA-256：`8172061b2a647dd8a179788830ef233944baee479bc7018f111064ad16d8f46f`。项目仅使用固定原始文本中与四六级社区词表整词吻合的中文—英文释义，不重新分发整份 CC-CEDICT。

修改内容：从 CC-CEDICT 中文条目中筛选四六级英语词的完整英文释义，检查中文键确实存在于青简拼音候选；人工记录义项说明，并用固定版本 ECDICT 的词性信息交叉核对。CC-CEDICT 本身不提供词性。运行映射保存在 `cccedict-expansion.tsv`，逐条来源行、原始英文释义、拼音信息及审校说明保存在 `batches/04-cc-cedict-reviewed.tsv`，构建统计保存在 `cccedict-manifest.json`。

逐条审校表另外含有 ECDICT 来源的词性核对信息。ECDICT 由 Skywind3000 发布，采用 MIT 许可，许可文本见 `ECDICT-LICENSE`；这些核对信息不进入 CC-CEDICT 运行映射。项目代码及其他词库文件各自适用其原有许可；CC BY-SA 4.0 仅适用于本批 CC-CEDICT 派生数据，不改变相邻文件的许可。
