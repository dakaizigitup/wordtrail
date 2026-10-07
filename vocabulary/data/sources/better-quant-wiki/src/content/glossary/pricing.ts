import type { Concept } from "../types";

export const pricing: Concept[] = [
  {
    slug: "emh",
    zh: "有效市场假说",
    en: "Efficient Market Hypothesis",
    abbr: "EMH",
    chapter: "pricing",
    importance: "core",
    definition:
      "价格已反映特定信息集：弱式（历史价格）、半强（公开信息）、强式（含内幕）。有效是相对一个信息集与一个成本模型而言的。",
    why: "它不是「不能赚钱」，而是「去掉风险、成本、选择性报告后，没有免费的超额」。量化的工作是寻找尚未被充分套利的结构，并诚实测出它是不是风险。",
    caveat:
      "拒绝随机游走 ≠ 拒绝有效。存在可预测性可以是风险溢价，也可以是摩擦。原文把 EMH 写成近乎宗教口号。",
    related: ["alpha", "capm", "factor-investing"],
  },
  {
    slug: "capm",
    zh: "资本资产定价模型",
    en: "Capital Asset Pricing Model",
    abbr: "CAPM",
    chapter: "pricing",
    importance: "core",
    definition:
      "若投资者只在乎均值方差、市场组合有效，则资产的期望超额收益与其市场 β 成正比。",
    formula: "\\mathbb{E}[R_i]-r_f=\\beta_i\\,(\\mathbb{E}[R_m]-r_f),\\quad \\beta_i=\\frac{\\mathrm{Cov}(R_i,R_m)}{\\mathrm{Var}(R_m)}",
    why: "这是单因子基准。业绩归因的第一行是：你的超额有多少只是 β。",
    caveat:
      "市场组合不可观测、β 不稳定、实证上低 β 反而有溢价（BAB）。CAPM 是参照系，不是真理。",
    related: ["beta", "alpha", "fama-french"],
  },
  {
    slug: "beta",
    zh: "贝塔",
    en: "Beta",
    abbr: "β",
    chapter: "pricing",
    importance: "core",
    definition:
      "资产收益对基准收益的回归斜率，度量系统性暴露，不是「波动率」本身。波动大但与市场无关，β 也可以低。",
    formula: "\\beta=\\frac{\\mathrm{Cov}(R_i,R_m)}{\\mathrm{Var}(R_m)}=\\rho_{i,m}\\frac{\\sigma_i}{\\sigma_m}",
    why: "对冲、杠杆、CAPM、指数增强，都要先知道 β。实现 β 用回归；预测 β 还要收缩、基本面调整。",
    caveat:
      "原文写「β=1 的股票加入组合不会增加任何风险」——错。它增加与市场相同的系统风险，只是不增加额外的相对波动。β 也不是投资组合方差的全部。",
    related: ["capm", "alpha", "unlevered-beta", "r-squared"],
  },
  {
    slug: "unlevered-beta",
    zh: "无杠杆贝塔",
    en: "Unlevered Beta",
    aliases: ["Asset Beta"],
    chapter: "pricing",
    importance: "supporting",
    definition:
      "剔除财务杠杆后的资产 β，便于跨资本结构比较或给项目估成本。",
    formula:
      "\\beta_U=\\frac{\\beta_E}{1+(1-t)D/E}\\quad(\\text{常见 Hamada 近似})",
    why: "比较两家公司的业务风险，不能直接比权益 β：杠杆更高的公司权益 β 自然更高。",
    caveat: "公式依赖债务 β=0、税率与杠杆稳定等假设。高信用风险时债务也有 β。",
    related: ["beta", "leverage", "wacc"],
  },
  {
    slug: "alpha",
    zh: "阿尔法",
    en: "Alpha",
    abbr: "α",
    chapter: "pricing",
    importance: "core",
    definition:
      "相对所选择定价模型的截距：不能被因子解释的超额收益。换模型，α 就变。",
    formula: "R_i-r_f=\\alpha_i+\\beta_i(R_m-r_f)+\\varepsilon_i",
    why: "这是主动管理的目标函数。没有明确基准与因子，就没有 α，只有「赚了钱」。",
    caveat:
      "样本内 α 很容易挖出来。真正的 α 必须样本外、扣成本、扣多重检验。许多「α」其实是未知因子或尾部风险。",
    related: ["capm", "beta", "backtesting", "factor-investing"],
  },
  {
    slug: "multi-factor-model",
    zh: "多因子模型",
    en: "Multi-Factor Model",
    chapter: "pricing",
    importance: "core",
    definition:
      "收益由多个共同因子线性（有时非线性）驱动。可分宏观因子、基本面因子、统计因子（PCA）。",
    formula: "R_i=\\alpha_i+\\sum_k \\beta_{ik}F_k+\\varepsilon_i",
    why: "风险归因、组合构建、中性化，当代量化的默认语言。单因子 CAPM 通常不够。",
    related: ["fama-french", "factor-investing", "multiple-regression"],
  },
  {
    slug: "fama-french",
    zh: "Fama–French 三因子",
    en: "Fama–French Three-Factor Model",
    chapter: "pricing",
    importance: "core",
    definition:
      "在市场因子之上加入规模（SMB）与价值（HML）。后来扩展为五因子（再加盈利 RMW、投资 CMA）。",
    formula: "R-r_f=\\alpha+b\\,\\mathrm{MKT}+s\\,\\mathrm{SMB}+h\\,\\mathrm{HML}+\\varepsilon",
    why: "学术与业界归因的共同基准。先问你的策略是不是只是小盘价值，再谈 α。",
    caveat: "因子定义（如何形成组合、是否包含金融股）会改变结论。HML 在近十年美股表现差，不自动等于「价值死了」。",
    related: ["multi-factor-model", "value-investing", "factor-investing"],
  },
  {
    slug: "factor-investing",
    zh: "因子投资",
    en: "Factor Investing",
    chapter: "pricing",
    importance: "core",
    definition:
      "系统性地暴露于经研究的收益驱动因子（价值、动量、质量、低波动、规模等），而不是选故事。",
    why: "把主动观点变成可重复、可风控的组合。多空因子与聪明贝塔（仅多头）是两条产品线。",
    caveat: "发表后衰减、拥挤、定义套利（你的价值不是我的价值）是真实风险。",
    related: ["fama-french", "momentum", "value-investing", "market-neutral"],
  },
  {
    slug: "value-investing",
    zh: "价值投资",
    en: "Value Investing",
    chapter: "pricing",
    importance: "supporting",
    definition:
      "以低于估计内在价值的价格买入。量化价值是其可规模化版本：用 B/P、E/P 等指标排序，而不是逐家读年报。",
    why: "HML 的经济故事。价值可能是风险（困境）也可能是行为错误定价——实证上两者都有文献。",
    related: ["fama-french", "graham", "pe-ratio", "cape"],
  },
  {
    slug: "passive-investing",
    zh: "被动投资",
    en: "Passive Investing",
    chapter: "pricing",
    importance: "supporting",
    definition:
      "跟踪指数、最小化主动偏离与费用。在成本与平均主动表现的意义上，对多数投资者是理性默认。",
    why: "市场组合是 CAPM 的锚。被动扩张会改变个股流动性与因子拥挤，本身成为结构。",
    related: ["emh", "capm", "alpha"],
  },
  {
    slug: "hedge",
    zh: "对冲",
    en: "Hedge",
    chapter: "pricing",
    importance: "core",
    definition:
      "建立相反暴露以降低某一风险因子。对冲是转移风险，不是免费保险：你付出溢价或放弃上行。",
    why: "Delta 对冲、汇率对冲、久期对冲，都是把不想要的风险卖出去，留下想要的 α。",
    caveat: "完美对冲只在模型里。基差、凸性、流动性与对手方会让对冲在最需要时失效。",
    related: ["delta-hedging", "gamma-hedging", "futures", "basis"],
  },
  {
    slug: "leverage",
    zh: "杠杆",
    en: "Leverage",
    chapter: "pricing",
    importance: "core",
    definition:
      "用借债或衍生品使经济暴露大于净资产。放大收益、亏损与破产概率，并把路径（中间回撤）变成生存问题。",
    formula: "\\text{名义暴露}=L\\times \\text{净值}",
    why: "很多「高夏普」策略的真实风险是杠杆 × 拥挤 × 流动性。LTCM 是教案。",
    related: ["leverage-ratio", "margin", "ltcm", "buying-on-margin"],
  },
  {
    slug: "leverage-ratio",
    zh: "杠杆率",
    en: "Leverage Ratio",
    chapter: "pricing",
    importance: "core",
    definition:
      "负债或总资产相对权益的倍数。银行监管、基金、公司财务各有不同口径（总资产/权益、债务/EBITDA 等）。",
    why: "同一策略，杠杆率决定你能挨过多少个 σ 的逆风。",
    related: ["leverage", "balance-sheet", "unlevered-beta"],
  },
  {
    slug: "volatility",
    zh: "波动性",
    en: "Volatility",
    abbr: "σ",
    chapter: "pricing",
    importance: "core",
    definition:
      "收益的离散程度，通常用标准差（已实现）或期权隐含（implied）。是风险的一个度量，不是全部（还有偏度、跳跃、流动性）。",
    formula:
      "\\sigma=\\sqrt{\\mathrm{Var}(r)},\\quad\\text{年化时通常乘}\\ \\sqrt{252}",
    why: "期权定价、仓位缩放（风险平价）、风控限额的共同输入。波动聚集意味着 σ 可预测，价格方向难预测。",
    caveat: "√252 假设独立同分布。有自相关或隔夜跳空时，年化是近似。高波动 ≠ 高 β。",
    related: ["vix", "variance", "implied-vol", "garch"],
  },
  {
    slug: "vix",
    zh: "VIX 指数",
    en: "CBOE Volatility Index",
    abbr: "VIX",
    chapter: "derivatives",
    importance: "core",
    definition:
      "由 S&P 500 期权价格复制的 30 天期望方差的年化平方根，是隐含波动的指数，不是已实现波动。",
    why: "风险偏好与尾部的温度计。VIX 期货结构（contango）使长期多 VIX 的 ETF 有严重负 carry。",
    caveat: "VIX 本身不可直接交易；交易的是期货与期权。把 VIX 当「恐慌」没问题，当交易标的必须懂期限结构。",
    related: ["vix-option", "implied-vol", "volatility-smile"],
  },
];
