# Reader's Seat

> 让 AI 站到读者的位置，把工作材料写成更容易理解、判断和行动的文档。

[English](README.md) · [更多示例](examples/quick-start.md)

[![Version](https://img.shields.io/badge/version-0.15.2-2563EB)](SKILL.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-16803C.svg)](LICENSE)
[![Validate](https://github.com/BobbyYue/reader-seat/actions/workflows/validate.yml/badge.svg)](https://github.com/BobbyYue/reader-seat/actions/workflows/validate.yml)

## 它解决什么问题

很多 AI 文档语句通顺，但读完仍然不知道：结论是什么、证据在哪里、哪些只是推测、接下来是否需要行动。

Reader's Seat 会围绕读者真正需要理解或判断的问题重组材料，同时保留事实、数字、范围和不确定性，不会为了让内容更有说服力而强化结论。

| 常见的原始表达 | Reader's Seat 会说清楚什么 |
| --- | --- |
| “版本发布当周，7 日留存从 42% 降至 38%，应该是版本导致的。” | 7 日留存同期下降 4 个百分点；目前只能确认时间上的同步变化，不能判断因果，还需要分层或对照数据。 |
| 半年总结中列出大量会议、看板和实验 | 区分做了什么、交付了什么、已有证据支持什么结果，以及哪些影响仍然未知。 |
| “方案 A 更先进，所以应该选 A。” | 各方案满足了哪些约束、主要取舍、决策条件、风险，以及是否缺少回滚信息。 |

## 适合哪些文档

| 你手里的材料 | 读者真正需要知道什么 |
| --- | --- |
| 新闻、访谈、行业资料 | 已确认事实、来源状态、时间和未知 |
| 技术方案、架构评审 | 约束、选项、取舍、风险和回滚条件 |
| 产品介绍、发布说明、PRD | 适用对象、解决的问题、已有能力和边界 |
| 项目汇报、复盘、绩效总结 | 工作、交付、结果、风险和下一步 |
| 数据分析、研究报告 | 指标口径、变化幅度、证据、不确定性和因果边界 |
| SOP、帮助文档、运行手册 | 前置条件、步骤、成功信号、异常分支和恢复路径 |

短消息润色、没有材料依据的内容扩写，以及脱离文档任务的纯视觉美化，不是它的主要用途。

## 在 Codex 中安装

```bash
git clone https://github.com/BobbyYue/reader-seat.git ~/.codex/skills/reader-seat
```

新建一个 Codex 任务后，可以显式调用：

```text
使用 $reader-seat 重写这段分析结论，读者是产品负责人。
保留指标、幅度和时间范围，区分观察到的事实、可能解释、因果判断和未知。
输出 Markdown。
```

在支持自动触发的 Agent 中，明确提出“从读者视角”或“让文档对读者更友好”也可能触发该 skill。

## 需要提供什么

多数情况下只需要四项信息：

```text
材料：需要处理的原文、数据或来源
读者：谁会阅读，已经了解哪些背景
目标：读者看完需要理解、判断或完成什么
格式：HTML、飞书、Word、Markdown、纯文本等
```

新闻、技术方案、产品文档、业务汇报、数据分析和 SOP 的提示词见[更多示例](examples/quick-start.md)。

## 默认输出规则

- 保留事实、数字、定义、负责人、承诺和不确定性。
- 区分观察、解释、因果、建议和未知。
- 标题提供正文能够支持的信息，不用悬念代替内容。
- 只有在视觉元素能降低定位、比较、理解或验证成本时才使用。
- 新建完整文档时默认输出自包含 HTML，除非用户指定其他格式。
- 用户没有指定语言时，沿用原材料的主要语言，而不是提示词语言。
- 未经明确授权，不会发布、覆盖或发送内容。

## 各文件夹提供什么功能

| 文件夹 | 提供的功能 |
| --- | --- |
| `.github/` | 在每次代码推送和合并请求时自动检查仓库。 |
| `agents/` | 帮助支持的 Agent 识别并展示 Reader's Seat。 |
| `assets/` | 提供自包含 HTML 模板、本地字体以及图表和流程图运行时。 |
| `config/` | 定义支持的文档场景、模块加载方式、Agent 适配设置和可校验的 skill 约束。 |
| `evals/` | 提供固定的触发、行为和跨 Agent 测试案例及评判标准。 |
| `examples/` | 提供可以直接改写使用的常见文档提示词。 |
| `references/` | 提供按场景、格式、标题、证据和视觉需要选择的详细写作规则。 |
| `scripts/` | 校验 skill、选择所需模块、创建 HTML 报告骨架并运行评测。 |

## 在其他 Agent 中使用

将仓库放到该 Agent 可读取的位置，并让它显式加载 `SKILL.md`。不同 Agent 的自动发现方式并不相同，具体评测方法见[跨 Agent 使用与稳定性](references/agent-portability.md)。

在至少两个明确命名的 Agent 通过相同冻结案例前，本仓库不声称已经实现跨 Agent 稳定输出。

## 更新与校验

```bash
cd ~/.codex/skills/reader-seat
git pull
python3 scripts/validate_skill.py
```

第三方字体和可视化运行时的来源与许可证见 [Third-Party Notices](assets/html/THIRD_PARTY_NOTICES.md)。
