# 活动复盘改进 · Issue #15

对应用户业务流程图中的“汇总数据 → AI 复盘 → 下一轮方案”。当前 GitHub 身份为 zhupaifan，成员 c，仅修改 AI 实现、AI 测试和 AI 文档。

## 基线与范围

- 实际 fetch 的 main：`2132fa30164d984e5de92c79420783ee6bd73dbd`。
- 依赖产品 PR #14：`224f264171ae1ae425269f7a26db256ff92b5d6d`。从 main 使用仓库 `start --member c --issue 15 --native --native-issue-verified` 建本人分支，再仅在本人分支 fast-forward 到该依赖。Issue 已通过当前账号的 GitHub API 核验开放且唯一负责人为 zhupaifan。
- 本轮差异仅在 `services/marketing-ai/`、`tests/ai/`、`docs/ai/`；未修改前后端、接口契约、协作规则或队友分支。PR 以 #14 的分支为 base，避免把其既有改动计入本轮。

## 行为

销售与报名分别计算目标相关的计数比，每项明确列出分子、分母及来源字段。课程 4 次报名、3 次到场显示 75%，销售 10 次咨询、5 次订单显示 50%；只称汇总计数比，不称去重用户转化率或营销效果。

缺失值不补零，零分母不计算，超过 100% 提醒核对口径，未知归因收入单独保留。无记录时仅给出数据不足事实并建议录入，不把残留 stats 传给模型。模型不能移除这些限制或确定的下一步建议。收入减退款从原始十进制数值计算，覆盖大金额小差额丢失分币精度的回归。

## 本次实际验证

使用 Python 3.12.14、Git 2.52.0；在仓库外 `/workspace/feiyi-ai-venv` 创建独立 venv，按 `services/api/requirements.txt` 安装现有固定依赖，未改依赖声明或锁文件。

| 检查 | 结果 |
| --- | --- |
| 原有协作基线 `python -m unittest discover -s tests -v` | 45 项：44 通过，1 项因 Linux 无 PowerShell 跳过 |
| 改动前 `python -m unittest discover -s tests/ai -v` | 20 项通过 |
| 新复盘单测在实现前运行 | 10 项中 9 项失败/错误，原有商家隔离检查通过；实现后 10 项全部通过 |
| 改动后 AI 标准库单测（engine + review） | 30 项通过 |
| `python -m pytest tests/ai tests/backend tests/e2e -q -o faulthandler_timeout=30` | 62 项全部通过，包含 2 项新增复盘 API 参数化用例 |
| `git diff --check` | 通过 |

API 用例经真实应用路由、独立 SQLite 数据库写入三组不同活动/商家指标，验证目标活动不会混入其他组数据；追加指标后新复盘更新而旧复盘内容不变。销售和报名两条路径都执行。

接口测试在受限沙箱内等待本地异步通信，无完成结果；停止本次启动的等待进程后，通过受支持的沙箱外执行运行，取得上述完整结果。不能把此前未完成的运行计作通过。测试有一项既有 Starlette/httpx 弃用提示。

## 未验证与协作要求

使用合成数据；模型边界采用模拟提供方，不消耗真实模型额度。不声称真实商家经营效果、渠道自动发布、线上部署或真实模型计费已验证。前端没有本轮改动，未重复其浏览器验收。GitHub CI 与真人审批以 PR 当前状态为准；依赖链不自动合并。
