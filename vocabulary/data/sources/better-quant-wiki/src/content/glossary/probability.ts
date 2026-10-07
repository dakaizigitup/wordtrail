import type { Concept } from "../types";

export const probability: Concept[] = [
  {
    slug: "conditional-probability",
    zh: "条件概率",
    en: "Conditional Probability",
    chapter: "probability",
    importance: "core",
    definition:
      "在已知事件 B 已发生的前提下，事件 A 发生的概率，记为 P(A|B)。它是几乎所有金融推断（从违约概率到信号有效性）的底层语言。",
    formula: "P(A\\mid B)=\\frac{P(A\\cap B)}{P(B)}\\quad(P(B)>0)",
    why: "量化里几乎没有无条件问题：你问的总是「给定这个信号 / 这组宏观状态，收益或违约的分布是什么」。",
    caveat:
      "P(A|B) 一般不等于 P(B|A)。把两者当成一回事，就是经典的检察官谬误，也是策略评估里最常见的逻辑错误之一。",
    related: ["joint-probability", "bayes-theorem", "probability-distribution"],
  },
  {
    slug: "joint-probability",
    zh: "联合概率",
    en: "Joint Probability",
    chapter: "probability",
    importance: "core",
    definition:
      "两个（或多个）事件同时发生的概率 P(A∩B)。若 A、B 独立，则联合概率等于边际概率之积。",
    formula:
      "P(A\\cap B)=P(A\\mid B)P(B)=P(B\\mid A)P(A)",
    why: "组合风险、多资产同时大跌、因子同时失效，都必须用联合分布而不是各自的边际分布来想。",
    caveat:
      "独立是很强的假设。金融市场里「平时近似独立、危机时高度相关」是常态，用独立乘积会系统性低估尾部。",
    related: ["conditional-probability", "correlation", "covariance"],
  },
  {
    slug: "bayes-theorem",
    zh: "贝叶斯定理",
    en: "Bayes' Theorem",
    chapter: "probability",
    importance: "core",
    definition:
      "用新证据 B 把先验 P(A) 更新为后验 P(A|B) 的恒等式。它不是一种「观点」，而是条件概率的重写。",
    formula:
      "P(A\\mid B)=\\frac{P(B\\mid A)\\,P(A)}{P(B)}=\\frac{P(B\\mid A)\\,P(A)}{\\sum_i P(B\\mid A_i)P(A_i)}",
    why: "回测里的「策略赢了所以有效」、风控里的「模型没报警所以没风险」，都要用贝叶斯想清楚：似然高不等于后验高，还取决于先验和假阳性。",
    caveat:
      "原文标题写成 Baye's Theorem，少了 s 的所有格。另：原文把条件概率说成「相似情况下某结果的可能性」，这不是定义。",
    related: ["conditional-probability", "joint-probability", "p-value"],
  },
  {
    slug: "probability-distribution",
    zh: "概率分布",
    en: "Probability Distribution",
    chapter: "probability",
    importance: "core",
    definition:
      "随机变量全部可能取值及其概率（离散：PMF；连续：PDF）的完整刻画。CDF F(x)=P(X≤x) 是更常用的工作对象。",
    why: "定价、风险、仓位，本质上都是在某个分布下求期望、分位数或尾部积分。只报一个均值没有分布，等于没有模型。",
    caveat:
      "收益分布通常不是正态：左偏、厚尾、波动聚集。用正态分布只是可计算的起点，不是市场事实。",
    related: ["normal-distribution", "uniform-distribution", "expected-value"],
  },
  {
    slug: "normal-distribution",
    zh: "正态分布",
    en: "Normal Distribution",
    abbr: "N(μ, σ²)",
    aliases: ["Gaussian"],
    chapter: "probability",
    importance: "core",
    definition:
      "由均值 μ 与方差 σ² 完全决定的钟形连续分布。独立同分布随机变量之和在温和条件下渐近正态（中心极限定理）。",
    formula:
      "f(x)=\\frac{1}{\\sigma\\sqrt{2\\pi}}\\exp\\!\\left(-\\frac{(x-\\mu)^2}{2\\sigma^2}\\right)",
    why: "CLT、回归误差、Black–Scholes 的对数收益假设、VaR 的解析公式，都从这里出发。它是工具，不是信仰。",
    caveat:
      "日收益的峰度通常远大于 3。用 ±2σ 当「95% 不会亏那么多」会在危机中破产。量化里更常对对数收益而不是价格本身谈正态。",
    related: ["central-limit-theorem", "empirical-rule", "z-score", "log-return"],
  },
  {
    slug: "uniform-distribution",
    zh: "均匀分布",
    en: "Uniform Distribution",
    chapter: "probability",
    importance: "supporting",
    definition:
      "在区间 [a,b] 上密度为常数 1/(b−a) 的分布。每个等长子区间概率相同。",
    formula: "X\\sim U[a,b]\\Rightarrow \\mathbb{E}[X]=\\frac{a+b}{2},\\ \\mathrm{Var}(X)=\\frac{(b-a)^2}{12}",
    why: "蒙特卡洛的原始随机数、无信息先验、以及把 CDF 反变换抽样时的底盘，都是均匀分布。",
    related: ["monte-carlo", "probability-distribution"],
  },
  {
    slug: "law-of-large-numbers",
    zh: "大数定律",
    en: "Law of Large Numbers",
    aliases: ["大数法则"],
    chapter: "probability",
    importance: "core",
    definition:
      "i.i.d. 且期望有限时，样本均值几乎必然收敛到真实期望。频率会逼近概率，但只在样本足够多且独立时成立。",
    formula:
      "\\bar X_n=\\frac{1}{n}\\sum_{i=1}^n X_i \\xrightarrow{\\text{a.s.}} \\mathbb{E}[X]",
    why: "这是「多做几次，边缘会显现」的数学版本，也是保险、做市库存、高频统计套利能存在的前提。",
    caveat:
      "金融市场的「样本」高度依赖、非平稳。把十年牛市的胜率当成概率，是对大数定律的误用。大数定律不保证小样本，也不消除尾部。",
    related: ["central-limit-theorem", "expected-value", "monte-carlo"],
  },
  {
    slug: "correlation",
    zh: "相关性",
    en: "Correlation",
    chapter: "probability",
    importance: "core",
    definition:
      "两个随机变量线性共变的方向与强度。日常说的「相关」在量化里默认指 Pearson 线性相关，不是一般依赖。",
    why: "组合分散化、因子暴露、对冲比率，第一步都是看相关结构。危机时相关会跳向 1，这比单个波动更致命。",
    caveat:
      "相关不是因果；零相关不是独立（可以有非线性依赖）；滚动相关极不稳定。原文把相关性和相关系数拆成两篇重复文章。",
    related: ["correlation-coefficient", "covariance", "multicollinearity"],
  },
  {
    slug: "correlation-coefficient",
    zh: "相关系数",
    en: "Correlation Coefficient",
    abbr: "ρ",
    chapter: "probability",
    importance: "core",
    definition:
      "把协方差除以两边标准差，得到无量纲的线性相关度量，取值 [−1,1]。",
    formula:
      "\\rho_{X,Y}=\\frac{\\mathrm{Cov}(X,Y)}{\\sigma_X\\sigma_Y}",
    why: "比较不同量纲的序列（收益率 vs 利差变化）时必须用 ρ 而不是协方差。回归里的 β 与 ρ 差一个波动率比。",
    caveat:
      "对异常值敏感。对数收益、秩相关（Spearman）在厚尾数据上往往更稳。高相关不意味着可交易：还要看延迟、成本和稳定性。",
    related: ["correlation", "covariance", "beta", "r-squared"],
  },
  {
    slug: "variance",
    zh: "方差",
    en: "Variance",
    abbr: "σ²",
    chapter: "probability",
    importance: "supporting",
    definition:
      "随机变量偏离其均值的平均平方距离，标准差的平方。组合方差把协方差矩阵全部装进来：wᵀΣw。",
    formula: "\\mathrm{Var}(X)=\\mathbb{E}[(X-\\mathbb{E}X)^2]",
    why: "均值—方差框架是组合理论的起点；方差掉期与方差溢价把「方差」本身变成可交易资产。",
    caveat:
      "平方项让方差对极端值极度敏感：一次崩盘可以主导整段样本方差。厚尾数据下「样本方差」本身的抽样波动就很大。",
    related: ["volatility", "covariance", "expected-value", "probability-distribution"],
  },
  {
    slug: "monte-carlo",
    zh: "蒙特卡罗模拟",
    en: "Monte Carlo Simulation",
    chapter: "probability",
    importance: "core",
    definition:
      "用随机抽样近似期望、概率或分位数的数值方法。当解析解不存在（路径依赖期权、组合 VaR、复杂约束）时是标准工具。",
    formula:
      "\\mathbb{E}[f(X)]\\approx\\frac{1}{N}\\sum_{i=1}^N f(X^{(i)}),\\quad X^{(i)}\\sim \\mathbb{P}",
    why: "定价、风险、组合优化的压力测试，很多只能模拟。误差大约按 1/√N 下降，方差缩减（对偶、控制变量、重要性抽样）比蛮力加次数更重要。",
    caveat:
      "垃圾分布进、垃圾数字出。模拟不能弥补错误的过程假设（例如用 GBM 生成真实的崩盘路径）。",
    related: ["law-of-large-numbers", "probability-distribution", "value-at-risk"],
  },
  {
    slug: "systematic-sampling",
    zh: "系统抽样",
    en: "Systematic Sampling",
    chapter: "probability",
    importance: "context",
    definition:
      "在有序列表上每隔 k 个抽一个（随机起点）。比简单随机抽样便宜，但若数据有周期，会严重偏倚。",
    why: "了解抽样偏差即可。量化里更常遇到的是时间序列的非随机抽样：只用交易日、只在开盘、只在事件后。",
    caveat:
      "价格序列有季节性、星期效应、到期日效应。机械地「每 5 根 K 线抽一根」可能正好踩上周期。",
    related: ["law-of-large-numbers", "autocorrelation"],
  },
  {
    slug: "coefficient-of-variation",
    zh: "变异系数",
    en: "Coefficient of Variation",
    abbr: "CV",
    chapter: "probability",
    importance: "supporting",
    definition:
      "标准差与均值之比，用来比较不同量纲或不同均值水平序列的相对离散度。",
    formula: "\\mathrm{CV}=\\frac{\\sigma}{\\mu}\\quad(\\mu\\neq 0)",
    why: "在均值显著不为零且同号时，比较相对风险比单看 σ 公平。例如比较两种费后收益流的稳定性。",
    caveat:
      "收益均值接近 0 时 CV 会爆炸，没有意义。夏普比率才是「每单位波动的超额收益」，不要用 CV 替代风险调整收益。",
    related: ["volatility", "sharpe-ratio", "expected-value"],
  },
  {
    slug: "p-value",
    zh: "P 值",
    en: "P-value",
    chapter: "statistics",
    importance: "core",
    definition:
      "在原假设 H₀ 为真时，得到与观测一样极端或更极端的统计量的概率。它不是「H₀ 为真的概率」，更不是效应大小。",
    formula: "p=P(\\text{统计量与观测一样极端或更极端}\\mid H_0)",
    why: "回测、因子检验、A/B 都必须报告：你看到的结果，在「其实没东西」的世界里有多常见。",
    caveat:
      "p<0.05 不是发现真理。多重检验、数据窥探、非平稳会让 p 值失效。原文把 P 值放在概率章、把假设检验放在统计章，二者必须合在一起用。",
    related: ["hypothesis-testing", "statistical-significance", "t-test"],
  },
  {
    slug: "t-test",
    zh: "t 检验",
    en: "t-test",
    chapter: "statistics",
    importance: "core",
    definition:
      "用 t 分布检验均值（或回归系数）是否等于某值。当方差未知、样本有限时，用样本标准差代替 σ，尾部比正态更厚。",
    formula:
      "t=\\frac{\\bar x-\\mu_0}{s/\\sqrt{n}}\\sim t_{n-1}\\quad(\\text{正态 i.i.d. 下})",
    why: "检验因子溢价是否为零、策略日均收益是否显著，最常用的就是 t。策略的 t 统计量 ≈ 夏普 × √T（数量级关系）。",
    caveat:
      "收益有厚尾和异方差时，名义 t 会过于乐观。至少用 HAC/Newey–West，或 bootstrap。样本重叠（滚动收益）会严重虚高 t。",
    related: ["z-test", "hypothesis-testing", "p-value", "regression"],
  },
  {
    slug: "z-score",
    zh: "Z 分数",
    en: "Z-score",
    chapter: "statistics",
    importance: "core",
    definition:
      "把观测值减去均值再除以标准差，得到以「几个 σ」为单位的位置。Altman Z-score 是完全不同的信用评分模型，不要混淆。",
    formula: "z=\\frac{x-\\mu}{\\sigma}",
    why: "横截面上把因子暴露、残差、价差标准化后才能比较、截尾、做 z-score 选股。",
    caveat:
      "用滚动均值/方差做 z，本质是假设局部平稳。波动突变时 z 会失真；要用稳健位置/尺度或对波动建模。",
    related: ["z-test", "normal-distribution", "empirical-rule"],
  },
  {
    slug: "z-test",
    zh: "Z 检验",
    en: "Z-test",
    chapter: "statistics",
    importance: "supporting",
    definition:
      "在方差已知（或 n 很大、靠 CLT）时，用标准正态做均值或比例检验。",
    formula: "z=\\frac{\\bar x-\\mu_0}{\\sigma/\\sqrt{n}}",
    why: "大样本均值检验的极限形式。实践中方差几乎总是未知，所以小样本用 t，大样本 t 与 z 接近。",
    related: ["t-test", "central-limit-theorem", "z-score"],
  },
  {
    slug: "calculus-derivative",
    zh: "导数（微积分）",
    en: "Derivative (calculus)",
    chapter: "derivatives",
    importance: "core",
    definition:
      "函数的瞬时变化率。期权希腊值、久期、凸性、梯度优化，全是导数或高阶导数。",
    formula: "f'(x)=\\lim_{h\\to 0}\\frac{f(x+h)-f(x)}{h}",
    why: "没有导数就没有敏感度：Delta、DV01、因子暴露的边际贡献都算不出来。",
    caveat:
      "原文在「概率论」下列了一条「衍生品 Derivative」，正文却是金融衍生品合约。金融 derivative 与 calculus derivative 是两个词。本站把二者拆开。",
    related: ["gamma", "duration", "financial-derivative"],
  },
];
