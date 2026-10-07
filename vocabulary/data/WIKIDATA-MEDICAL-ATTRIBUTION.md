# Wikidata CC0 与 MeSH 医学译词来源

## 来源与许可

本批只使用 Wikidata 的结构化条目标签和 MeSH 外部编号，不使用 Wikidata 图片、长描述或其他媒体。Wikidata 结构化数据按 CC0 1.0 提供；署名虽非 CC0 的强制条件，仍在此致谢 Wikidata contributors：

- Wikidata 数据许可：<https://www.wikidata.org/wiki/Wikidata:Licensing>
- NLM MeSH 2026 术语及使用条件：<https://www.nlm.nih.gov/databases/download/terms_and_conditions_mesh.html>
- NLM MeSH 2026 Descriptor XML：<https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/xmlmesh/desc2026.zip>

MeSH 是美国国家医学图书馆 NLM 的产品。NLM 允许免费使用 MeSH 数据，但要求注明 NLM 和版本；本项目使用 2026 英文主题词和树编号，并非 NLM 官方产品，也不代表 NLM 背书。未使用 MeSH 中文翻译/MTMS 文件。

## 对应关系和修改

中文标签与 MeSH 英文主题通过同一 Wikidata 条目上的 MeSH `P486` 外部编号建立对应。每条采用记录还固定了 Wikidata QID、实体修订号、中文标签语言、MeSH ID 及树编号；构建时再次检查实体修订快照中的 `P486`、标签和值。发现候选需要同时满足：

- 中文标签已是本地拼音候选键，且中文键还有新增容量；
- MeSH 首选词有本地英式或美式音标；
- 固定 ECDICT 有该英文词的名词词性记录；
- 与已有译词不存在重复中文—英文对应；
- 逐项判断词义和专业范围后明确接受。

这里的中文翻译来源是 Wikidata 的中文标签；ECDICT 仅提供词性存在证据，不用其短义替代或校正 Wikidata 译文。只提取 25 条短映射和24个新的医学标签成员，不带入定义、例句或完整词表；`capillaries` 在上一批已有医学标签，本批只增加“毛细血管”这一中文入口。标签继承 MeSH 主题范围，部分词属于环境、技术或社会心理主题，不代表医学课程或完整医学术语表。

固定文件：

- [`sources/wikidata/mesh-label-query-20261007.json`](sources/wikidata/mesh-label-query-20261007.json)，SHA-256 `754cf2c43a6dc6b21f44b09c24f95bb8ad37d0857364d33e200614c83ff39569`。
- [`sources/wikidata/mesh-entity-revisions-20261007.json`](sources/wikidata/mesh-entity-revisions-20261007.json)，SHA-256 `1c331dd24ca8cb862d614535998b716471eab9107aa32ed58c7d97c6757b3d01`。
- [`sources/mesh/desc2026.zip`](sources/mesh/desc2026.zip)，SHA-256 `bb73dfdfe78cbfcd692ef399bb6df24750327ff62c4f53574826c56ba3d6a3f3`。

MeSH 标签查询使用 Wikidata Query Service 的 SPARQL `wdt:P486`，查询英文及 `zh-hans`、`zh-cn`、`zh-sg` 标签。固定查询逻辑为：

```sparql
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?item ?mesh ?zh ?en WHERE {
  ?item wdt:P486 ?mesh ; rdfs:label ?zh, ?en .
  FILTER(LANG(?zh) IN ("zh-hans", "zh-cn", "zh-sg"))
  FILTER(LANG(?en) = "en")
}
```

候选发现后通过 Wikidata `wbgetentities` 固定实体修订和 P486 记录。2026-10-07 的查询快照含409条标签绑定，实体修订快照覆盖48个候选 QID。源快照只包含结构化数据；完整接受、拒绝和暂缓理由位于 [`batches/22-wikidata-medical-reviewed.tsv`](batches/22-wikidata-medical-reviewed.tsv)，构建统计及每个接受 QID 的修订号位于 [`wikidata-medical-manifest.json`](wikidata-medical-manifest.json)。

本次 48 组技术候选中，逐项接受 25 组，排除 5 组，暂缓 18 组。运行时只编译 [`wikidata-medical-expansion.tsv`](wikidata-medical-expansion.tsv) 和 [`wikidata-medical-tags.tsv`](wikidata-medical-tags.tsv)；输入时不读取来源 JSON 或审核表。用以下命令离线重建：

```powershell
python scripts/build_wikidata_medical_batch.py --discover
python scripts/build_wikidata_medical_batch.py
```

## 扩展医学译词批次23

2026-10-07 将标签检索范围扩至1,326个本机有英美音标及 ECDICT 名词记录的 MeSH 2026 主题编号，查询 Wikidata Query Service 的 `P486`（MeSH Descriptor ID）与英语、`zh-cn`、`zh-hans`、`zh-sg` 标签。快照有1,964条标签关联，固定了870个相关 Wikidata 实体的修订号、日期、标签和 MeSH 编号。查询范围和查询文本一并归档，构建器检查来源散列、范围数量、查询结果 ID 和实体修订中的 P486/标签。

157组标签关联通过本地拼音、音标、ECDICT 名词词性和每键容量预筛；已有基础词头不重复入待审队列后，48组进入逐条审核。接受19组映射，3组排除、26组暂缓；18个英文词头此前没有词库映射，18个获得新的医学成员标签。一条新增映射对应的词头已有其他运行记录。接受的标签跨越临床、解剖、心理和化学/药物主题；不能据此推算完整医学覆盖率。

批次23的固定来源：

- [`sources/wikidata/mesh-label-query-20261007.rq`](sources/wikidata/mesh-label-query-20261007.rq)：SPARQL 查询文本，SHA-256 `0f4b7ab22e7cc7571788a63b9ccd86f99a299f4a6f0ee22c9005f04a7b50dada`。
- [`sources/wikidata/mesh-query-scope-20261007.txt`](sources/wikidata/mesh-query-scope-20261007.txt)：1,326个 MeSH 编号，SHA-256 `1888452af8bac6dcf1f311c7cf67824fc192d6b1baaa32712964a4a137850533`。
- [`sources/wikidata/mesh-label-query-full-20261007.json`](sources/wikidata/mesh-label-query-full-20261007.json)：固定查询结果，SHA-256 `49f1f8b6e0954fa5cca25a6d692a5c1ae6e62be8d642c12dfd6d3391fde3a497`。
- [`sources/wikidata/mesh-entity-revisions-full-20261007.json`](sources/wikidata/mesh-entity-revisions-full-20261007.json)：实体修订快照，SHA-256 `15d513a3db152c780c8df663e6adf78f6ee839cc7c815ca095c942fcb575a9f4`。
- [`sources/mesh/desc2026.zip`](sources/mesh/desc2026.zip)：NLM MeSH 2026 Descriptor XML，SHA-256 `bb73dfdfe78cbfcd692ef399bb6df24750327ff62c4f53574826c56ba3d6a3f3`。

157组机械预筛及基础词头重复状态见 [`batches/23-wikidata-medical-prefilter.tsv`](batches/23-wikidata-medical-prefilter.tsv)；逐条送审的48组候选和接受/排除/暂缓说明见 [`batches/23-wikidata-medical-candidates.tsv`](batches/23-wikidata-medical-candidates.tsv) 与 [`batches/23-wikidata-medical-reviewed.tsv`](batches/23-wikidata-medical-reviewed.tsv)。只将19条短映射与18条新增标签写入运行 TSV，不复制定义、例句或完整 MeSH/Wikidata 数据。离线确定性重建命令：

```powershell
python scripts/build_wikidata_medical_batch_2.py --discover
python scripts/build_wikidata_medical_batch_2.py
```
