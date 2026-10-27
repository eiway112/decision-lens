# 来源清单与脱敏规则

> 本文件回答两件事：透镜卡的判据从哪来；公开前哪些内容必须处理掉。

## 一、来源标注纪律

每张透镜卡的 `来源` 字段只有两种取值，**不得混淆**：

- `[公开] <URL>` —— 该判据可在给定 URL 处核对。
- `[自撰]` —— 本技能自撰判据，无外部来源。

**把自撰标成公开，比不标更坏**（诚实账优先于漂亮账）。三卷 42 张卡中，标注 `[自撰]` 的占多数，这是如实交代，不是欠账。

## 二、公开来源清单

| 用途 | 来源 |
|---|---|
| 问题形态的因果维度（clear/complicated/complex/chaotic/disorder） | Cynefin framework（Kurtz & Snowden 2003；Snowden & Boone 2007, HBR）https://en.wikipedia.org/wiki/Cynefin_framework |
| 「高杠杆」的可判阶梯（12 级） | Meadows, Leverage Points: Places to Intervene in a System https://donellameadows.org/archives/leverage-points-places-to-intervene-in-a-system/ |
| 要素⑥ pre-mortem 三步 | Klein, Performing a Project Premortem, HBR 2007-09 https://hbr.org/2007/09/performing-a-project-premortem |
| 置信度须可被评分 | Scoring rule / Brier score https://en.wikipedia.org/wiki/Scoring_rule |
| 「先写下什么证据会推翻」的纪律 | Preregistration (science) https://en.wikipedia.org/wiki/Preregistration_(science) |
| 指标成为目标后不再是好指标 | Goodhart's law https://en.wikipedia.org/wiki/Goodhart%27s_law |
| 缺陷注入（mutator / killed / mutation score） | Mutation testing https://en.wikipedia.org/wiki/Mutation_testing |
| 心智模型的边界写法范式 | Farnam Street, Mental Models https://fs.blog/mental-models/ ｜ Circle of Competence https://fs.blog/circle-of-competence/ |
| 路由定义与 human-in-the-loop 判据 | Anthropic, Building effective agents https://www.anthropic.com/engineering/building-effective-agents |
| 渐进披露与脚本定位 | Anthropic, Equipping agents for the real world with Agent Skills https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills |
| 多约束决策的三阶段骨架 | Multiple-criteria decision analysis（Belton & Stewart 2002）https://en.wikipedia.org/wiki/Multiple-criteria_decision_analysis |

> 本技能不隶属于上表任何机构；引用仅作来源标注，不构成背书或商标使用。

## 三、脱敏规则（元判据 M7 的执行）

透镜库由一批实践条目裁减而来。公开前按三类判定：

| 类别 | 处置 |
|---|---|
| 含本机绝对路径 / 身份事实 | **不分发**，脱敏后方可 |
| 依赖特定内部语境才成立 | **不分发** |
| 去掉语境后仍能改变其他项目的决策 | **可分发** |

**三问按序判定，顺序不可换。**

据此落地到本技能的三条硬规则：

1. **内部项目名与内部文件名一律不出现在任何卡中**——它们属于第 1、2 类。
2. **逐字引文一律删除**。判据的效力来自「主张 + 做法 + 证伪条件」，不来自原文措辞。删掉引文不损失任何决策能力。
3. **数值类结论不采信**，除非能回指到可核验的公开处。

## 四、未入选条目的去向

裁撤的 48 条不删除，留两处：

- **仓内**：三卷末尾的「未入选条目」表，只列标题 + 一句裁撤理由（已脱敏，可公开、可审计）。
- **仓外**：原始底稿（含内部出处与逐字引文）单独留存，不进本仓、不公开。
