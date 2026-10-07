# 批次21：医学词汇与标签

批次21采用美国国家医学图书馆 NLM 的 MeSH 2026 英文主题词表，给现有可输入译词补充“医学”标签，并补充一小批准确的医学译词。只使用官方 Descriptor XML 的英文主题词和分类树，不使用 MeSH 中文翻译文件。

本地固定词库交叉后，得到256组带本机拼音、英美音标和 ECDICT 同词性短义证据的候选。逐项筛选后纳入75组中英映射，新增74个英文词头；7组明显误配排除，174组因中文一般释义不足以对应具体 MeSH 概念而暂缓。MeSH 首选英文主题词与本机已有拼音可达释义相交，另新增1,079个医学标签归属。标签数不等同医学词汇覆盖率；目前没有可靠完整分母。

接受的译词包括：`脱发 → alopecia`、`腋窝 → axilla`、`结石 → calculi`、`脑电图 → electroencephalography`、`肾上腺素 → epinephrine`、`增生 → hyperplasia`、`授精 → insemination`、`突触 → synapses`、`疫苗 → vaccines` 等。出现明显误义的候选，例如 `amygdala → 扁桃体`，没有进入运行词库。

MeSH 官方条款允许免费使用并要求署名和标明版本；随源码保存固定的2026归档文件、SHA-256 和来源说明。MeSH 提供英文概念范围；中文短义和词性来自 MIT 许可 ECDICT，两者的来源分工见[署名与修改记录](../vocabulary/data/MESH-ATTRIBUTION.md)。逐项候选、接受/排除/暂缓理由和标签对应证据分别保存在 `vocabulary/data/batches/21-mesh-medical-*.tsv`，重建统计见 `mesh-medical-manifest.json`。

运行时只编译75行映射和1,079行标签 TSV；键盘查询使用已初始化的精确哈希索引，不扫描 MeSH XML 或审计表。医学标签参与已有译词优先规则，仍只改变英文译词顺序，不改变中文候选顺序。没有更新或安装电脑版，也没有生成发布包。

复建命令：

```powershell
python scripts/build_mesh_medical_batch.py --discover
python scripts/build_mesh_medical_batch.py
```

本机缺少 Cargo/MSVC 链接工具，Rust 单元测试不能在当前环境执行；数据生成、来源哈希、候选与清单一致性可以本地复核。
