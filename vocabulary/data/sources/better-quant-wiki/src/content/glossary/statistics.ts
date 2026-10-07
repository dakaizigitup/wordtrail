import type { Concept } from "../types";

export const statistics: Concept[] = [
  {
    slug: "expected-value",
    zh: "期望值",
    en: "Expected Value",
    abbr: "E[X]",
    chapter: "statistics",
    importance: "core",
    definition:
      "按概率加权的平均结果。它是定价的第一原理：套利定价与风险中性定价都是在某个测度下求期望再贴现。",
    formula:
      "\\mathbb{E}[X]=\\sum_i x_i p_i\\quad\\text{或}\\quad \\int x\\,f(x)\\,dx",
    why: "策略的「平均赚多少」、期权的风险中性价格、信用损失的 EL，都是期望。决策永远对期望加风险，而不是对单次实现。",
    caveat:
      "期望可以被尾部绑架：正期望策略仍可破产（方差/杠杆过大）。几何期望（对数效用）在重复博弈、仓位选择里往往比算术期望更相关。",
    related: ["law-of-large-numbers", "present-value", "kelly-criterion"],
  },
  {
    slug: "covariance",
    zh: "协方差",
    en: "Covariance",
    chapter: "statistics",
    importance: "core",
    definition:
      "两个变量如何一起偏离各自均值。组合方差的交叉项全部是协方差，这是现代组合理论的骨架。",
    formula:
      "\\mathrm{Cov}(X,Y)=\\mathbb{E}[(X-\\mathbb{E}X)(Y-\\mathbb{E}Y)]",
    why: "n 个资产的风险不是 n 个方差，而是 n×n 协方差矩阵。分散化是否有效，完全取决于非对角元。",
    caveat:
      "样本协方差在资产多、时间短时是噪声矩阵，必须收缩或用因子结构。协方差非平稳，危机中会整体上移。",
    related: ["correlation-coefficient", "beta", "variance-inflation-factor"],
  },
  {
    slug: "linear-relationship",
    zh: "线性关系",
    en: "Linear Relationship",
    chapter: "statistics",
    importance: "supporting",
    definition:
      "Y 可写成 a+bX+误差。斜率 b 是 X 每变化一单位时 Y 的平均变化。相关度量的是线性强度，不是一般单调或非线性依赖。",
    formula: "Y=a+bX+\\varepsilon",
    why: "CAPM、多因子、久期对冲，第一版都是线性。线性是可解释、可交易的起点。",
    caveat:
      "期权收益、杠杆、涨跌停、违约，都是非线性。用线性相关去对冲期权组合会在该对冲时失效。",
    related: ["regression", "nonlinearity", "correlation"],
  },
  {
    slug: "nonlinearity",
    zh: "非线性",
    en: "Nonlinearity",
    chapter: "statistics",
    importance: "core",
    definition:
      "输出对输入的响应不是比例关系：凸性、阈值、交互项、制度切换都是非线性。",
    why: "期权的 Gamma、债券凸性、杠杆约束、崩盘时的相关跳变，都让线性模型在关键时刻错得最狠。",
    caveat:
      "「加点平方项」不是建模非线性风险的全部。制度转换、尾部依赖（copula 的上/下尾）往往更重要。",
    related: ["gamma", "convexity", "linear-relationship"],
  },
  {
    slug: "central-limit-theorem",
    zh: "中心极限定理",
    en: "Central Limit Theorem",
    abbr: "CLT",
    chapter: "statistics",
    importance: "core",
    definition:
      "独立、方差有限的随机变量之和（或均值），标准化后依分布收敛到标准正态。这是 t/z 检验和大样本推断的地基。",
    formula:
      "\\sqrt{n}\\,(\\bar X_n-\\mu)/\\sigma \\xrightarrow{d} N(0,1)",
    why: "为什么很多估计量可以当正态用：因为它们是平均。这也是蒙特卡洛误差呈钟形的原因。",
    caveat:
      "方差无限（稳定分布、极端厚尾）时 CLT 不成立。金融日收益的「有限方差」本身就可疑；收敛也很慢。依赖数据要用混合中心极限或 HAC。",
    related: ["law-of-large-numbers", "normal-distribution", "z-test"],
  },
  {
    slug: "hypothesis-testing",
    zh: "假设检验",
    en: "Hypothesis Testing",
    chapter: "statistics",
    importance: "core",
    definition:
      "先规定原假设 H₀ 与备择 H₁，用数据计算检验统计量，再根据 H₀ 下的抽样分布做拒绝/不拒绝决策。不拒绝 ≠ 证明 H₀ 为真。",
    why: "因子是否存在、alpha 是否为零、两段波动是否相同，都是检验问题。没有检验的回测只是故事。",
    caveat:
      "先看数据再选假设，p 值作废。多个因子一起挖，必须做多重检验校正（Bonferroni、FDR、Haircut Sharpe）。",
    related: ["p-value", "statistical-significance", "confidence-interval"],
  },
  {
    slug: "statistical-significance",
    zh: "统计显著性",
    en: "Statistical Significance",
    chapter: "statistics",
    importance: "core",
    definition:
      "在预设的第一类错误率 α（常取 5%）下拒绝 H₀。显著只说明「不像纯噪声」，不说明「足够大到能赚钱」。",
    why: "用来过滤明显的运气。但不能替代经济显著性：成本、容量、衰减之后，显著的 2bp 可能毫无意义。",
    caveat:
      "样本越大，越小的效应也会显著。量化论文里堆满显著因子，交易里活下来的很少，因为显著 ≠ 可投资。",
    related: ["p-value", "hypothesis-testing", "t-test"],
  },
  {
    slug: "confidence-interval",
    zh: "置信区间",
    en: "Confidence Interval",
    abbr: "CI",
    chapter: "statistics",
    importance: "core",
    definition:
      "由数据构造的随机区间。95% 置信是指：若重复同样实验，约 95% 的区间会盖住真参数。不是「真参数有 95% 概率落在这个已实现区间里」。",
    formula:
      "\\bar x \\pm t_{n-1,1-\\alpha/2}\\,\\frac{s}{\\sqrt{n}}",
    why: "只报一个夏普 1.2 没有用，必须报区间。很多「年化 20%」的区间其实穿过 0。",
    caveat:
      "原文式的频率派解释经常被写成「参数有 95% 可能在里面」。那是贝叶斯可信区间的语言，前提不同。",
    related: ["hypothesis-testing", "t-test", "expected-value"],
  },
  {
    slug: "sharpe-ratio",
    zh: "夏普比率",
    en: "Sharpe Ratio",
    abbr: "SR",
    chapter: "statistics",
    importance: "core",
    definition:
      "每单位总波动换来的平均超额收益。年化时用 √T 缩放；分子分母必须同频率、同口径（含费、含无风险利率的取法）。",
    formula:
      "\\mathrm{SR}=\\frac{\\mathbb{E}[R-R_f]}{\\sigma_{R-R_f}}",
    why: "策略比较的第一把尺子，并且直接连着显著性：t ≈ SR × √T。三年的 SR 1 和十年的 SR 1，证据强度完全不同。",
    caveat:
      "夏普对负偏、厚尾策略系统性偏友好：卖期权、carry 在崩盘前夏普都很高。挖过多个因子后要看 haircut Sharpe。别忘扣成本与容量。",
    related: ["t-test", "confidence-interval", "volatility", "backtesting"],
  },
  {
    slug: "empirical-rule",
    zh: "经验法则",
    en: "Empirical Rule",
    aliases: ["68-95-99.7"],
    chapter: "statistics",
    importance: "supporting",
    definition:
      "近似正态时，约 68%/95%/99.7% 的质量落在 μ±1σ/2σ/3σ。它是心算工具，不是风险限额。",
    why: "快速检查：若日 σ=1%，±2σ 大约对应 2% 的「日常」波动。用来建立数量级，不是用来设止损。",
    caveat:
      "对金融收益，2σ 事件远比正态更频繁。用经验法则做风控，等于假设你最不该假设的东西。",
    related: ["normal-distribution", "z-score", "volatility"],
  },
  {
    slug: "chi-square",
    zh: "卡方统计量",
    en: "Chi-square Statistic",
    abbr: "χ²",
    chapter: "statistics",
    importance: "supporting",
    definition:
      "标准化平方和在正态假设下服从 χ²。用于方差检验、拟合优度、以及作为 F 检验的构件。",
    formula:
      "\\sum_{i=1}^k \\frac{(O_i-E_i)^2}{E_i}\\ \\sim\\ \\chi^2_{k-1}\\quad(\\text{拟合优度})",
    why: "检验残差是否白噪声、波动模型是否校准、离散状态的经验频率是否匹配，都会用到。",
    related: ["hypothesis-testing", "anova"],
  },
  {
    slug: "regression",
    zh: "回归分析",
    en: "Regression Analysis",
    chapter: "statistics",
    importance: "core",
    definition:
      "用一个或多个解释变量描述 E[Y|X]。量化里最常用的是线性回归：因子暴露、对冲比率、业绩归因都是回归。",
    formula: "Y=X\\beta+\\varepsilon,\\quad \\hat\\beta=(X^\\top X)^{-1}X^\\top Y",
    why: "把「看起来一起动」变成可估计、可检验、可交易的暴露。没有回归就没有因子模型。",
    caveat:
      "回归给的是条件均值，不是因果。遗漏变量、内生性、前视偏差，会让系数看起来漂亮但完全不能实盘。",
    related: ["ols", "multiple-regression", "r-squared", "beta"],
  },
  {
    slug: "ols",
    zh: "最小二乘法",
    en: "Ordinary Least Squares",
    abbr: "OLS",
    chapter: "statistics",
    importance: "core",
    definition:
      "选择使残差平方和最小的系数。在经典假设下，OLS 是线性无偏估计里方差最小的（高斯–马尔可夫）。",
    formula: "\\hat\\beta=\\arg\\min_b \\,\\|Y-Xb\\|^2",
    why: "默认估计器。对冲比率、CAPM β、Fama–French 都先跑 OLS。",
    caveat:
      "异方差、自相关时 OLS 仍可一致，但标准误错误，必须用稳健/HAC 标准误。有共线性时系数不稳。厚尾时要考虑稳健回归或分位数回归。",
    related: ["regression", "multiple-regression", "autocorrelation"],
  },
  {
    slug: "r-squared",
    zh: "R 平方",
    en: "R-squared",
    abbr: "R²",
    aliases: ["决定系数", "Coefficient of Determination"],
    chapter: "statistics",
    importance: "core",
    definition:
      "模型解释了因变量方差的多大比例。一元回归里 R² 等于相关系数的平方。",
    formula:
      "R^2=1-\\frac{\\sum e_i^2}{\\sum (y_i-\\bar y)^2}=\\rho^2_{y,\\hat y}",
    why: "看 CAPM 对一只股票解释了多少；R² 低意味着特异质风险大，指数对冲很差。",
    caveat:
      "加变量 R² 只升不降，所以多元要用调整 R²。高 R² 可以来自过拟合或共同趋势。预测任务更应看样本外 R²。原文把 R² 和「决定系数」写成两篇重复。",
    related: ["regression", "correlation-coefficient", "beta"],
  },
  {
    slug: "multiple-regression",
    zh: "多元线性回归",
    en: "Multiple Linear Regression",
    chapter: "statistics",
    importance: "core",
    definition:
      "多个解释变量同时进入线性模型。每个系数是「控制其他变量后」的偏效应。",
    formula: "Y=\\beta_0+\\beta_1 X_1+\\cdots+\\beta_k X_k+\\varepsilon",
    why: "这就是多因子：同时控制市场、规模、价值后，看动量还有没有 alpha。",
    caveat:
      "控制什么变量是建模决策，不是统计自动给出的。把未来信息放进 X，就是前视偏差。",
    related: ["regression", "multicollinearity", "fama-french", "ols"],
  },
  {
    slug: "multicollinearity",
    zh: "多重共线性",
    en: "Multicollinearity",
    chapter: "statistics",
    importance: "core",
    definition:
      "解释变量之间高度线性相关，导致系数方差爆炸、符号乱跳，但整体拟合仍可能很好。",
    why: "行业哑变量+市值、久期+期限、多个宏观指标一起塞进回归时几乎必然发生。你会「每个因子都不显著，但模型 R² 很高」。",
    caveat:
      "共线性伤害的是系数解释，不一定伤害预测。若目标是预测，ridge/主成分可能优于硬删变量。",
    related: ["variance-inflation-factor", "multiple-regression", "r-squared"],
  },
  {
    slug: "variance-inflation-factor",
    zh: "方差膨胀因子",
    en: "Variance Inflation Factor",
    abbr: "VIF",
    chapter: "statistics",
    importance: "supporting",
    definition:
      "把第 j 个系数的方差相对「无共线性」膨胀了多少。VIF_j = 1/(1−R²_j)，R²_j 来自用其他 X 回归 X_j。",
    formula: "\\mathrm{VIF}_j=\\frac{1}{1-R^2_j}",
    why: "诊断该不该信某个因子系数。经验上 VIF>5 或 10 就要警惕。",
    related: ["multicollinearity", "r-squared", "multiple-regression"],
  },
  {
    slug: "anova",
    zh: "方差分析",
    en: "Analysis of Variance",
    abbr: "ANOVA",
    chapter: "statistics",
    importance: "supporting",
    definition:
      "把总平方和拆成「模型解释的」与「残差」部分，用 F 检验看组间差异或回归是否整体显著。",
    why: "回归软件输出的 F 统计量就是 ANOVA。用来回答「这组因子合在一起有没有解释力」，而不是单个系数。",
    related: ["regression", "chi-square", "hypothesis-testing"],
  },
  {
    slug: "autocorrelation",
    zh: "自相关",
    en: "Autocorrelation",
    aliases: ["序列相关", "Serial Correlation"],
    chapter: "statistics",
    importance: "core",
    definition:
      "同一序列在不同滞后期之间的相关。收益率若有显著自相关，就意味着可预测（或微观结构噪声）；残差若有自相关，OLS 标准误作废。",
    formula:
      "\\rho_k=\\frac{\\mathrm{Cov}(r_t,r_{t-k})}{\\mathrm{Var}(r_t)}",
    why: "均值回归与动量都是自相关结构。波动聚集是平方收益的自相关。这是时间序列量化的第一张体检表。",
    caveat:
      "重叠样本（用滚动 20 日收益当观测）会人为制造巨大自相关。日收益自相关弱，不代表周/月频率或波动没有结构。",
    related: ["mean-reversion", "momentum", "ols", "heteroskedasticity"],
  },
  {
    slug: "heteroskedasticity",
    zh: "异方差",
    en: "Heteroskedasticity",
    chapter: "statistics",
    importance: "supporting",
    definition:
      "误差的方差不是常数，而随水平、时间或状态变化。金融时间序列里几乎总是如此：波动聚集就是最直观的异方差。",
    why: "异方差下 OLS 系数仍可一致，但标准误错误、检验失真。White/HC 稳健标准误或 HAC 是默认动作，GARCH 是进一步的建模。",
    caveat:
      "把异方差当「小问题」会系统性高估 t 值。残差平方对自变量或时间作图，是最便宜的诊断。",
    related: ["ols", "autocorrelation", "garch", "volatility"],
  },
  {
    slug: "garch",
    zh: "GARCH 模型",
    en: "GARCH",
    chapter: "statistics",
    importance: "supporting",
    definition:
      "让条件方差自身成为自回归过程的波动模型：今天的大波动预示明天的大波动（波动聚集），而收益率水平仍近乎不可预测。",
    formula:
      "\\sigma_t^2=\\omega+\\alpha\\,\\varepsilon_{t-1}^2+\\beta\\,\\sigma_{t-1}^2",
    why: "风险平价、期权交易、VaR 的前置滤波器。α+β 接近 1 描述波动的高度持续性；标准化残差还可以再接厚尾（t 分布）。",
    caveat:
      "GARCH 拟合的是波动，不是方向，别指望它预测涨跌。结构突变（体制切换）会让参数看起来「永久持续」。",
    related: ["volatility", "autocorrelation", "heteroskedasticity", "value-at-risk"],
  },
  {
    slug: "merton-model",
    zh: "默顿模型",
    en: "Merton Model",
    chapter: "derivatives",
    importance: "core",
    definition:
      "把公司股权看成以企业资产为标的、以负债面值为行权价的看涨期权；债务则是无风险债减去看跌（看跌–看涨平价）。由此给信用风险一个结构定价。",
    formula:
      "E=V\\,N(d_1)-Ke^{-rT}N(d_2),\\quad d_{1,2}=\\frac{\\ln(V/K)+(r\\pm\\sigma_V^2/2)T}{\\sigma_V\\sqrt{T}}",
    why: "这是结构信用模型的原型，也是 KMV/EDF 一类违约距离的思想来源。它把期权与公司金融接在一起。",
    caveat:
      "原文放在「统计学」下是分类错误。公式里的 σ 必须是资产波动率 σ_V，不是股票收益波动率；后者只是估计 σ_V 的输入。默顿与 Black–Scholes 共享公式，但经济含义是企业价值与资本结构。",
    related: ["financial-derivative", "put-option", "leverage", "implied-vol"],
  },
];
