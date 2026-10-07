# 批次30：NAER 经济学术语

本批固定国家教育研究院《Economics Terminology》CSV。政府资料开放平台将其说明为英中经济学术语表，提供机关为国家教育研究院，页面标明政府资料开放授权条款第1版；页面最后更新于2025-12-16。[数据集说明](https://data.gov.tw/en/datasets/15405) · [授权条款](https://data.gov.tw/license)

## 复核结果

源 CSV 共7,357条。筛选英文单词时要求本机至少有一地音标、本机 ECDICT 有精确名词义项、译词经过繁简转换后与完整义项一致、中文键存在于本机拼音候选，并且没有超过每键扩词上限。随后逐项判断是否属于有实际价值的经济、金融、劳动或商业译词。

253组候选满足完整词义和输入条件，其中189组原本已有完全相同映射；其余63组逐条审校后，纳入28组、排除12组、暂缓23组。纳入项涉及11个此前没有的英文词头，并为23个此前没有商务标签的词头增加商务分类。暂缓项多为通用词，或需要更完整上下文才能确认经济学专义；排除项包括含义不合、与商务经济无关的条目。专业词表没有统一完整分母，本批不报告专业覆盖率。

| 中文输入 | 英文译词 |
| --- | --- |
| 旷工、谈判、泡沫、佣金 | absenteeism, bargaining, bubbles, commissions |
| 竞争、消费、收敛、协调、公司 | competition, consumption, convergence, coordination, corporations |
| 扭曲、侵占、执行、均衡、诱因 | distortion, embezzlement, enforcement, equilibrium, incentives |
| 补偿、创新、清算、调解、合并 | indemnity, innovation, liquidation, mediation, merger |
| 流动性、有价证券、转包、补助 | mobility, securities, subcontracting, subsidization |
| 保证、剩余、纺织品、运输 | surety, surplus, textiles, transportation |
| 保证 | warranty |

原始 CSV 和门户元数据的 SHA-256、逐条候选和决定、精简运行映射均保存在 `vocabulary/data/`。运行时只加载28条精简中英映射与已审核标签，不扫描源词表；译词仍由现有音标和本地拼音键约束。授权署名和修改说明见[`NAER-ECONOMICS-ATTRIBUTION.md`](../vocabulary/data/NAER-ECONOMICS-ATTRIBUTION.md)，可复建统计见[`naer-economics-manifest.json`](../vocabulary/data/naer-economics-manifest.json)。

## 输入与构建验证

批次生成器为[`build_naer_economics_batch.py`](../scripts/build_naer_economics_batch.py)。共享词库测试验证28条映射与商务来源标签，并确认选择商务标签不会改变中文候选文字。Windows 补丁和 Android 安装包按既定计划留到词汇批次全部完成后再构建。
