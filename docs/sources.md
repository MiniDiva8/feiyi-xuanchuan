# 官方资料与核对记录

核对日期：2026-10-30。教程中的界面名称与支持范围据此编写；个人账号的实际可用性仍需逐人登录验证。

- [当前 Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environments)：桌面/Web 创建、Save/Publish、独立任务、已有任务保留状态、仓库刷新、Only me、个人连接。
- [Issue 到可审查 PR](https://learn.chatgpt.com/use-cases/issue-to-tested-pr)：明确范围、记录基线、实际验证、准备环境后发布，集成可用且授权时创建草稿 PR。
- [Codex GitHub Code Review](https://learn.chatgpt.com/docs/third-party/github)：独立的自动审查设置与 AGENTS.md 审查规则；不替代真人审批。
- [仓库名规则](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository)：最多 100 字符，仅 ASCII 字母、数字、点、横线、下划线。中文“非遗宣传”保留在项目名与描述中。
- [邀请个人仓库协作者](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository)：Free 私有仓库可添加协作者；邀请接受后才有访问。
- [个人仓库权限](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/permission-levels-for-a-personal-account-repository)：Owner 与 Collaborator；私有个人仓库协作者为 write，细分角色需组织方案。
- [分支保护计划限制](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)：私有仓库强制保护取决于支持计划。
- [GitHub CLI create](https://cli.github.com/manual/gh_repo_create)：--private；不把创建成功当作成员/保护/Cloud 全部就绪。
- [GitHub CLI PR](https://cli.github.com/manual/gh_pr_create)：--draft、--body-file、--head、--base、--reviewer。
- [GitHub CLI checks](https://cli.github.com/manual/gh_pr_checks)：bucket 状态与 pending 退出码 8；缺失检查不等于通过。
- [actions/checkout](https://github.com/actions/checkout/blob/main/README.md) 与 [actions/setup-python](https://github.com/actions/setup-python)：核对到当前示例使用 v7；本套件目标为 GitHub-hosted runners，不部署自托管 runner。
