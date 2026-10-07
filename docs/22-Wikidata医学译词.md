# 医学译词第二段：Wikidata 与 MeSH

本批从 Wikidata 中文标签与 NLM MeSH 2026 英文主题词的编号对应中，新增 **25 组可由本地拼音输入的中英映射**，其中24个英文词头此前没有运行时映射；另一个 `capillaries` 已在上一批映射并带有医学标签，本批新增“毛细血管”这个中文入口。候选发现阶段有48组通过本地拼音、至少一种本地音标、ECDICT 名词词性和词键容量检查；逐项复核后接受25组、排除5组、暂缓18组。运行词库新增24个医学标签成员。

新增词包括：

`毛细血管 → capillaries`、`感染 → infections`、`排尿 → urination`、`疣 → warts`、`经络 → meridians`、`聚合物 → polymers`、`过滤 → filtration`、`激光器 → lasers`、`微波 → microwaves`、`塑料 → plastics`、`气体 → gases`、`焦油 → tars`、`潜水 → diving`、`奶嘴 → pacifiers`、`斩首 → decapitation`、`灾害 → disasters`、`爆炸 → explosions`、`洪灾 → floods`、`龙卷风 → tornadoes`、`山崩 → landslides`、`森林 → forests`、`职业 → occupations`、`丧偶 → widowhood`、`错觉 → illusions`、`聚合 → polymerization`。

Wikidata 仅作为 CC0 中文标签来源；每条对应都通过同一条目的 MeSH P486 编号和实体修订再次核验。NLM MeSH 仅提供英文主题范围和医学标签依据。ECDICT 在本批只核验英文名词词性，不充当中文翻译来源。明显不够精确或范围容易误导的词保留在逐项审核表中，例如“角→horns”“董事→trustees”被排除，“蛋→eggs”等较宽泛候选暂缓。

运行时只增加25行映射和24行医学标签；来源快照、修订信息与审核表不进入按键时的查询路径。中文候选顺序不变，选择医学类别时仅提高对应英文译词优先级。两个 TSV 合计约2.3 KB。构建及来源细节见[署名说明](../vocabulary/data/WIKIDATA-MEDICAL-ATTRIBUTION.md)、[批次清单](../vocabulary/data/wikidata-medical-manifest.json)和[逐项复核表](../vocabulary/data/batches/22-wikidata-medical-reviewed.tsv)。

本次没有打包或安装电脑版。当前环境没有 Cargo，因此 Rust 构建和运行时测试尚未执行；数据生成、来源修订、MeSH 编号、拼音可达性、音标、词性及文件散列已由本地构建脚本核验。
