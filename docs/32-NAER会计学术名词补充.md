# 批次32：NAER 会计学术名词

本批固定国家教育研究院《会计学学术名词》（dataset 15404）CSV 快照，页面元数据更新于 2026-08-12，采用政府资料开放授权条款第1版。来源与署名详见[NAER 会计词表说明](../vocabulary/data/NAER-ACCOUNTING-ATTRIBUTION.md)。原始 CSV 有 4,878 条，SHA-256 为 `46eaea4143811919253f94cd86062dcd49a9376bbe8ee85ac8c514a5d00a9869`。

筛选要求单词有本地英式或美式音标、ECDICT 精确名词义、可用拼音键及每键容量；繁体中文经 OpenCC 转简体并与本地词义精确匹配。4,878 条来源记录中得到 191 组可核验词义，其中144组中英对应已经存在；45组新映射候选逐条审校，接受22组、排除12组、暂缓11组。新增3个英文词头。另将174个可核验来源词头逐个审查领域归属：133个获得商务来源标签，31个排除、10个暂缓；其中66个是此前没有商务标签的新成员。

映射仅从候选译词中优先展示，不改动中文候选顺序。运行时代码只编译22行映射和133行紧凑标签，不载入4,878条 CSV。会计词表没有统一完整分母，因此本批不宣称覆盖会计术语的固定百分比。逐条决定见 [`32-naer-accounting-reviewed.tsv`](../vocabulary/data/batches/32-naer-accounting-reviewed.tsv) 和 [`32-naer-accounting-tags-reviewed.tsv`](../vocabulary/data/batches/32-naer-accounting-tags-reviewed.tsv)；来源散列及重建命令见 [`naer-accounting-manifest.json`](../vocabulary/data/naer-accounting-manifest.json)。

## 索引体积与主机查询基准

同一 Windows 优化版 Rust 标签索引基准在纳入批次前后各运行一次。唯一词头从 12,356 增至 12,373；合并后的紧凑标签表从 138,310 增至 138,622 字节，增加 312 字节。基准每批对9个候选做18次查询并保持顺序，HashMap 的 p50/p95/p99 从 1.5/1.7/2.4 微秒变为 1.6/2.7/3.1 微秒；三项候选顺序断言均通过。初始化分别为1.77毫秒和1.92毫秒。该结果是 Windows 主机微基准，不包含 Android 的 JNI、键盘界面或手机冷启动测量，不能代替设备实测。
