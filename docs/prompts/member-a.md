# MiniDiva8 的新 Cloud 任务提示

把下面的 ISSUE_NUMBER 和 english-slug 替换成实际任务。只在你自己的个人 Cloud 环境运行。

```text
以我自己的 GitHub MiniDiva8 连接，为 MiniDiva8/feiyi-xuanchuan 实现 Issue #ISSUE_NUMBER。
先读取 AGENTS.md、apps/web/AGENTS.md、Issue 和验收条件，确认 Issue 开放且唯一 Assignee 是 MiniDiva8。
检查是否已有同一 Issue 的活动分支/PR，避免重复实现。我的成员键是 a。三人均可修改前端、后端、AI及公共代码；本次以Issue目标和验收范围为准。根AGENTS的全目录授权已撤销子模块历史“只改本模块”限制，保留技术和数据规则。
先检查工作区并拉取最新 origin/main，记录 SHA，再执行：
python scripts/collab.py start --member a --issue ISSUE_NUMBER --slug english-slug
如果 gh 不可用，先用我的原生 GitHub 连接核验上述事实，然后使用 --native --native-issue-verified；不要复制凭据或用 --offline 绕过真实仓库检查。
如果工作树有未提交变化、权限缺失或范围不明确，保留文件并报告具体阻塞。
实现后运行实际检查，用 save 提交，用 preflight / 必要时 sync 检查最新 main 与冲突。
我授权你只将本 Issue 范围的变更普通推送到本人的任务分支，并创建或更新草稿 PR；使用 publish 或可用的 Cloud 原生 Create PR。
PR 写明 Closes #ISSUE_NUMBER、改动、实际测试、未验证项、起始 main 和当前 head SHA。
跨模块修改要核对接口与测试，不强推、不自动合并、不公开仓库、不部署、不新增授权。
```
