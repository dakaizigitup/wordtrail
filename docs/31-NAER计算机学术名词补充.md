# 批次31：NAER 计算机学术名词

本批固定国家教育研究院《两岸对照名词—计算机学术名词》开放数据集（15275）。[官方数据页](https://data.gov.tw/dataset/15275)列出繁体中文与中国大陆译名两栏，许可为[政府资料开放授权条款第1版](https://data.gov.tw/license)；页面元数据更新于2026-08-12。固定 CSV 共1,532条记录，SHA-256 为 `d8d65ba4097d45dd1c5d6b737fc942a1bd92d74d76ce6d6fb5348001b11b75bd`。

## 审校结果

按本机拼音、至少一地音标和 ECDICT 完整中文词义筛选，得到371组精确中英对应。其中289组原词库已经收录；另有82组尚未收录，2组因该中文键达到扩词容量上限而不进入审校队列。余下80组逐项判断后接受40组、排除8组、暂缓32组。新映射包含3个此前没有的英文词头：`morphing`、`radix`、`replication`。另有49个此前没有计算机分类的词获得新标签；62条来源记录覆盖全部新增映射与经审校的已有映射。

例如，新增 `中断 → break`、`亮度 → luminosity`、`响应 → response`、`基数 → radix`、`缓冲区 → buffer`、`解析 → resolve`、`语法 → syntax` 和 `顺序 → sequence`。容易混淆的译项没有硬加：`permission → 允许`、`undo → 取消`、`spoofing → 哄骗`等保留在审校记录中，避免把不自然或不精确的译词放进运行词库。

运行时只载入40条审核通过的短映射和62条计算机类别来源记录，不扫描原始 CSV。所有其他考试/专业标签仍可与计算机标签并存，中文候选原顺序保持不变。逐条依据、排除与暂缓原因、哈希和可重建命令见[`NAER-COMPUTER-ATTRIBUTION.md`](../vocabulary/data/NAER-COMPUTER-ATTRIBUTION.md)、[`naer-computer-manifest.json`](../vocabulary/data/naer-computer-manifest.json)以及`vocabulary/data/batches/31-naer-computer-*`。

本批只更新共享词库源码，尚未构建 Android 或 Windows 安装包；Windows 版本按计划留到词汇批次全部完成后再打包与安装。
