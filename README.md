# 非遗宣传 · 三人协作

私有仓库：[MiniDiva8/feiyi-xuanchuan](https://github.com/MiniDiva8/feiyi-xuanchuan)

三人分别使用自己的 GitHub、Codex 账号和个人 Cloud 环境，以 GitHub 的 main、Issues、PR 为共同状态。

**先读 [六步加入指南](docs/加入协作_原生流程.md)。** 默认使用 GitHub 和 Codex Cloud 原生功能，不需要先运行协作脚本。

1. 两位成员各自接受 GitHub write 邀请。
2. 三人各自连接仓库并创建、发布个人 Cloud 环境。
3. 用 Issue 指派单人任务，从最新 main 建立独立分支。
4. 实际测试并提交草稿 PR，其他成员评审。
5. 由人核对 CI、冲突并 Squash merge。
6. 下一任务重新读取最新 main。

建议分工：MiniDiva8 前端 apps/web/；donghaochen45-pixel 后端 services/api/；zhupaifan AI services/marketing-ai/。公共接口在 packages/contracts/ 协商。

当前仓库交付的是协作基础配置，业务功能尚未实现。已有脚本、模板、CI 和详细教程全部保留：
- [AGENTS 规则](AGENTS.md)
- [详细 Cloud 教程](docs/cloud-onboarding.md)
- [管理员配置与可选 CLI](docs/admin-setup.md)
- [测试与未验证事项](docs/verification.md)
- [分工及评审规则](docs/team-workflow.md)

本地 45 项测试已通过，首次 GitHub-hosted Ubuntu/Windows 测试已通过。三个个人 Cloud 环境与三人真实端到端验收仍须分别确认。
私有仓库强制分支保护申请返回 403；保持 private、未购买服务，合并前由人核对检查与评审。

测试：`python -m unittest discover -s tests -v`。scripts/ 中的自动化工具是可选的，不代替本人授权、实际 CI 或真人评审。
