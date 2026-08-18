# Reader's Seat

> 从读者的位置出发，把零散工作材料整理成让人容易理解、判断和行动的完整文档。

[English](README.md) · [提示词示例](examples/quick-start.md) · [安装](#安装)

[![Version](https://img.shields.io/badge/version-0.16.0-2563EB)](SKILL.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-16803C.svg)](LICENSE)
[![Validate](https://github.com/BobbyYue/reader-seat/actions/workflows/validate.yml/badge.svg)](https://github.com/BobbyYue/reader-seat/actions/workflows/validate.yml)

**原始材料 → 完整文档 → 读者形成正确判断**

任何能够加载 `SKILL.md`，或能够按明确规则执行任务的 Agent，都可以使用 Reader's Seat。它不依赖某个特定模型、厂商或调用语法。

## 它为读者改变什么

很多 AI 文档语句通顺，但读者仍然需要自己寻找结论、核对证据并判断下一步。

| 找到重点 | 验证判断 | 采取行动 |
| --- | --- | --- |
| 主要结论出现在前面。 | 判断能够对应到证据、范围和不确定性。 | 待决策问题和下一步不会超出证据边界。 |

## 看三个实际场景

| 场景 | 输入材料 | 生成的完整文档 |
| --- | --- | --- |
| **项目进展** | 周报、里程碑计划、会议记录、问题清单、交付数据 | **项目进展报告**<br>当前结论 · 里程碑 · 进度 · 阻塞 · 待决策事项 · 有证据支持的下一步 |
| **数据分析结论** | 指标定义、查询结果、图表、方法说明、数据限制 | **数据分析报告**<br>分析问题 · 结论与幅度 · 证据 · 数据口径 · 其他解释 · 不确定性 · 下一步验证 |
| **技术路线** | 业务需求、技术约束、候选架构、性能测试、成本和迁移问题 | **技术决策文档**<br>待决策问题 · 约束 · 方案比较 · 取舍 · 推荐条件 · 实施影响 · 回滚 · 未解决风险 |

它也适用于新闻和行业资料、产品文档、项目复盘、绩效总结、SOP、运行手册和帮助文档。

> [!NOTE]
> Reader's Seat 面向有实质内容的文档。短消息润色、没有材料依据的内容扩写，以及脱离文档任务的纯视觉美化，不是它的主要用途。

## 安装

### 方式一：让 Agent 安装

把下面的指令发给具有文件和命令执行能力的 Agent：

```text
从 https://github.com/BobbyYue/reader-seat 安装 Reader's Seat。
将它放到当前 Agent 支持的 skill 目录中，文件夹名称保持为 reader-seat，
然后确认 SKILL.md 可以被加载。已有同名安装时不要直接覆盖，先询问我。
如果环境中有 Python，安装后运行 python3 scripts/validate_skill.py。
```

如果 Agent 不能安装本地 skill，请使用下面的手动方式。

### 方式二：手动 Git Clone

先设置当前 Agent 使用的 skill 目录，再克隆仓库：

```bash
AGENT_SKILLS_DIR="/path/to/your-agent/skills"
git clone https://github.com/BobbyYue/reader-seat.git "$AGENT_SKILLS_DIR/reader-seat"
```

克隆后，按照该 Agent 的说明注册目录，或让 Agent 显式加载 `reader-seat/SKILL.md`。不同 Agent 的自动发现方式并不相同。

## 使用

多数情况下只需要四项信息：

```text
使用 Reader's Seat 创建或重写这份文档。
材料：需要处理的原文、数据、文件或来源链接
读者：谁会阅读，已经了解哪些背景
目标：读者看完需要理解、判断或完成什么
格式：HTML、飞书、Word、Markdown、纯文本等
```

常见文档场景的完整写法见[提示词示例](examples/quick-start.md)。

## 默认输出

| 格式 | 语言 | 证据 | 视觉元素 |
| --- | --- | --- | --- |
| 没有指定时生成自包含 HTML | 没有指定时沿用原材料的主要语言 | 保留事实、数字、定义、负责人、承诺和不确定性 | 只有在降低定位、比较、理解或验证成本时才使用 |

未经明确授权，Reader's Seat 不会发布、覆盖或发送内容。

## 在不同 Agent 上使用

写作规则集中在 `SKILL.md` 及其引用模块中。不同 Agent 可以调整发现方式、输入方式和输出方式，但不应改写内容规则。

仓库提供三种稳定性评测方式：

| Agent 接口 | 评测方式 |
| --- | --- |
| 命令从标准输入读取提示词，并从标准输出返回结果 | `command-stdin` 适配器 |
| 命令读取提示词文件，并写入结果文件 | `command-files` 适配器 |
| GUI 或暂不支持命令调用 | `manual` 人工提示词包 |

具体方法见[跨 Agent 使用与稳定性](references/agent-portability.md)。在至少两个明确命名的 Agent 通过相同冻结案例前，本项目不声称已经实现跨 Agent 稳定输出。

<details>
<summary><strong>仓库结构、校验和许可证</strong></summary>

| 文件夹 | 提供的功能 |
| --- | --- |
| `.github/` | 在每次代码推送和合并请求时自动检查仓库。 |
| `agents/` | 帮助支持的 Agent 识别并展示 Reader's Seat。 |
| `assets/` | 提供自包含 HTML 模板、本地字体以及图表和流程图运行时。 |
| `config/` | 定义文档场景、模块加载方式、Agent 适配设置和可校验的 skill 约束。 |
| `evals/` | 提供固定的触发、行为和跨 Agent 测试案例及评判标准。 |
| `examples/` | 提供可以直接改写使用的常见文档提示词。 |
| `references/` | 提供按场景、格式、标题、证据和视觉需要选择的详细规则。 |
| `scripts/` | 校验 skill、选择模块、创建 HTML 报告骨架并运行评测。 |

校验安装：

```bash
python3 /path/to/reader-seat/scripts/validate_skill.py
```

更新安装：

```bash
git -C /path/to/reader-seat pull
```

第三方字体和可视化运行时的来源与许可证见 [Third-Party Notices](assets/html/THIRD_PARTY_NOTICES.md)。

</details>
