# 批次23：扩展 Wikidata × MeSH 医学译词

本批把 Wikidata CC0 中文标签与 NLM MeSH 2026 的 P486 编号交叉筛选范围扩大到1,326个本机具备音标和 ECDICT 名词词性证据的 MeSH 主题。固定快照包含1,964条中英标签关联，覆盖870个 Wikidata 实体修订。原始查询和修订数据均留档；运行时不加载这些研究快照。

157组标签候选还须同时满足本地拼音键、至少一个英美音标、名词词性、每个中文候选键未超容量且不存在重复中英映射。去掉基础词库已有的英文词头后，48组进入逐项审核：接受19组映射、排除3组、暂缓26组。新增18个此前未映射的英文词头和18个医学标签归属；一组映射对应的英文词此前已有词库记录。中文候选顺序不变。

新增映射如下：

| 中文 | 英文 | 中文 | 英文 | 中文 | 英文 |
|---|---|---|---|---|---|
| 醇 | alcohols | 碱 | alkalies | 春药 | aphrodisiacs |
| 牙医 | dentists | 低血压 | hypotension | 注射 | injections |
| 泻药 | laxatives | 性冲动 | libido | 乳头 | nipples |
| 农药 | pesticides | 安慰剂 | placebos | 粉末 | powders |
| 处方 | prescriptions | 败血症 | sepsis | 梦游 | somnambulism |
| 注射器 | syringes | 片剂 | tablets | 疗法 | therapeutics |
| 意志 | volition |  |  |  |  |

直接的 P486 对应只是候选证据，不代表中文标签都适合作为输入释义。例如 `缠绕 → constriction`、`蛋 → eggs`、`角 → horns` 因义项不准确或过于含混而排除；一般自然、人际关系或社会词条即使出现在 MeSH 中，也没有仅凭分类标签自动收录。接受词条都有精确拼音入口、本地音标和 ECDICT 名词词性记录；ECDICT 只核验词性，不替换 Wikidata 中文标签。

专业词汇没有一份固定完整分母，因此不报告“医学词汇覆盖率”。MeSH 还包含化学、环境和社会心理主题；`medical` 是来源主题标签，不代表完整临床课程范围。`Therapeutics` 的 MeSH 范围是疾病治疗或预防相关程序，见 [NLM MeSH 2026 条目](https://meshb.nlm.nih.gov/record/ui?lang=en&ui=D013812)。

来源、查询范围、SHA-256 和逐条处理理由见[Wikidata / MeSH 署名说明](../vocabulary/data/WIKIDATA-MEDICAL-ATTRIBUTION.md)、[`wikidata-medical-manifest-2.json`](../vocabulary/data/wikidata-medical-manifest-2.json)、[157组预筛记录](../vocabulary/data/batches/23-wikidata-medical-prefilter.tsv)、[48组审核记录](../vocabulary/data/batches/23-wikidata-medical-reviewed.tsv) 和[`build_wikidata_medical_batch_2.py`](../scripts/build_wikidata_medical_batch_2.py)。本批只更新共享词库源码；依照安排，电脑版尚未打包或安装。
