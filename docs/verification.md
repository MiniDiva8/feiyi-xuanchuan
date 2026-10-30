# 验证状态

本文件区分本地真实 Git 实测、固定 API 数据测试、真实 GitHub 以及三个真实 Codex Cloud 环境。尚未运行的检查不算通过。

## 本次环境检查
- 已有 AI创新大赛 项目：无提交、master、无远程；保留。
- 新套件：D:/Codex/Projects/HeritageMarketingCollab，独立 Git 根目录。
- Git 2.54.0.windows.1、Python 3.12、GitHub CLI 2.93.0 可用。
- GitHub 插件 MiniDiva8 可识别本人；Fqin9 明确排除在本项目之外。
- 初始受限上下文报告 CLI 登录失败；用户授权官方网页登录并成功以 MiniDiva8 登录。允许联网的上下文已实测读取仓库；网络受限不能据此断言凭据无效。

## 验证矩阵
| 项目 | 验证方式 | 当前状态 |
|---|---|---|
| 最新 main 起点、独立分支、普通提交 | 临时 bare + 独立 clone 的真实 Git 命令 | 45 项完整本地测试通过（2026-10-30） |
| 越界、脏树、跨模块重命名、冲突无损拦截 | 自动化行为测试 | 45 项完整本地测试通过（2026-10-30） |
| 三人并行分支、集成、后续新任务取最新 main | 临时三 clone 仿真，非真实 GitHub PR | 已在完整测试中实测通过；另附本地仿真 JSON |
| PR 当前 head、CI、评审、未知状态 | 固定 GitHub API 形状的数据测试 | 通过不等于实际 GitHub/Cloud 验收 |
| PowerShell/Bash 包装器及 YAML | 本机运行/解析 | Windows PowerShell 与 Git Bash --help 通过；YAML 结构解析通过；Cloud/Linux 运行未验证 |
| 私有仓库创建及代码上传 | 真实 GitHub API / Git push | 私有仓库已真实创建并回读验证；尚未上传代码 |
| 两个协作者接受邀请 | 两人本人账号查看仓库 | 未验证，必须本人完成 |
| GitHub-hosted Windows/Ubuntu Actions | 实际 workflow run | 未验证，等待真实仓库运行 |
| main 分支保护 | GitHub 设置/API 回读 | 未验证，受账号计划限制 |
| MiniDiva8 的个人 Cloud 环境 | 本人创建、测试并 Publish | 未验证 |
| donghaochen45-pixel 的个人 Cloud 环境 | 本人创建、测试并 Publish | 未验证 |
| zhupaifan 的个人 Cloud 环境 | 本人创建、测试并 Publish | 未验证 |
| 三人真实 Cloud → PR → 人工合并 → 新任务 | 三人逐项记录 head/main SHA 与 PR | 未验证；本套件不会自动合并 |

## 本次真实边界
- 完整命令 python -m unittest discover -s tests -v：45 tests，OK，87.617 秒；Windows 本机运行。
- 三 clone 仿真创建独立提交和分支，向临时 bare origin 普通推送；只在临时集成 clone 模拟合并。
- 非冲突同步保留功能提交；故意制造共享契约冲突时 preflight/sync 不改变 HEAD、索引与工作文件。
- Bash 启动器已修复 Windows 的 python3 App Execution Alias 存在但不可执行的情况；实际 Git Bash 启动通过。
- GitHub CLI API 已验证 MiniDiva8/feiyi-xuanchuan 为 PRIVATE、isEmpty=true、Actions enabled=true。
- 当前 Codex GitHub 插件读取新私有仓库返回 404；尚未证明该连接具备新仓库访问。须在本人 Cloud 仓库选择/授权流程核实。
- 个人 GitHub 计划 API 未返回明确计划名称；不声称已启用私有分支保护。
- 没有自动合并真实代码，没有部署服务器，没有共享账户凭据。

## 三人验收填写表
| 成员 | 接受邀请/读取仓库 | 个人环境发布 | 新任务 main SHA | PR / head SHA | 实际 CI | 同伴审批 | 人工合并后的新任务 main SHA |
|---|---|---|---|---|---|---|---|
| MiniDiva8 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 |
| donghaochen45-pixel | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 |
| zhupaifan | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 | 待填 |

只填写可公开给队友的常规仓库/PR 链接和提交 SHA；不要填访问令牌、内部环境标识或授权链接。

## 独立审查后的最终本地结果
- 初版 38 项通过后，独立审查另复现 4 项 Important 问题。
- 已逐项写出失败回归、修复并重跑；最终完整 45 项通过，87.617 秒。
- 新增覆盖：隐藏暂存改动、部分暂存保留、有效 pushurl、忽略文件碰撞、PR CI 的 workflow/event 来源。
- GitHub 私有仓库创建已完成；首次上传、邀请、设置、实际 PR/Actions 与三人 Cloud 验收仍分别等待操作或本人确认。
