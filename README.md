# 非遗宣传 · GitHub + Codex Cloud 三人协作

服务产品销售与体验课程商家的 AI 营销平台。本仓库当前交付的是**协作开发基础设施**，尚未实现营销平台业务功能。

远程目标：**MiniDiva8/feiyi-xuanchuan，公开仓库**。三名开发者使用自己的 GitHub、Codex 账号和个人 Cloud 环境。无需 SSH 服务器、自建云服务器或共享文件系统。

## 从这里开始

1. 所有者先读 [管理员配置](docs/admin-setup.md)，核对当前仓库、上传配置及两位队友的write权限。
2. 每个人读 [三人分别操作教程](docs/cloud-onboarding.md)，接受访问邀请，用本人账号创建并发布自己的 Cloud 环境。
3. 开发前读 [AGENTS.md](AGENTS.md) 和 [分工及评审规则](docs/team-workflow.md)。
4. 查看 [实测与未验证项目](docs/verification.md)，区分本地仿真、实际 GitHub 和实际 Cloud 验收。

## 主责参考与共同代码权限

| 成员 | GitHub | 主责参考目录 | 普通 PR 备份评审者 |
|---|---|---|---|
| a | MiniDiva8 | apps/web/ | zhupaifan |
| b | donghaochen45-pixel | services/api/ | MiniDiva8 |
| c | zhupaifan | services/marketing-ai/ | donghaochen45-pixel |

**三人均可修改前端、后端、AI及公共代码**，表中分工不限制目录。保留一任务一负责人和独立分支；至少一名其他成员评审当前提交，测试通过后由人合并。详见[本次规则调整及同步方法](docs/team-wide-access.md)。

## 日常快捷命令

在 Windows 终端里可让 Codex 代执行下列命令；也可直接使用 PowerShell 包装器。

```powershell
python scripts/collab.py doctor
python scripts/collab.py start --member a --issue 1 --slug merchant-dashboard
python scripts/collab.py save --message "feat: merchant dashboard"
python scripts/collab.py preflight
python scripts/collab.py sync
python scripts/collab.py publish --title "实现商家工作台"
python scripts/collab.py check-pr --pr 1
python scripts/collab.py board
```

等效包装器：`./collab.ps1 doctor`；Linux/Cloud：`bash ./collab.sh doctor`。

start 从最新 origin/main 开始；save 做范围检查、项目检查、明确暂存和提交；preflight 无损检查冲突；sync 只同步本人的功能分支；publish 普通推送并创建/复用草稿 PR。**没有自动合并命令。** main 合并由人在 GitHub 确认。

已有 Codex GitHub 连接器不一定代表 gh CLI 已登录。Cloud 中如 gh 不可用，按教程使用原生 GitHub/PR 功能，保留相同的 Issue、分支和检查约定。

## 环境要求与验证

- Python 3.11+、Git 2.38+；CLI 远程自动化另需本人登录的 GitHub CLI。
- 本套件不需要第三方 Python 包、OpenAI API Key、SSH 或云服务器。
- `python -m unittest discover -s tests -v`
- `python scripts/simulate_team.py`：只在临时目录运行三 clone Git 仿真，不代表三个真实账户或 Cloud 环境通过。
- CI 预置 Windows/Ubuntu 双平台检查；必须等待实际 Actions 结果，才能声称云端 CI 通过。
- 业务代码落地后，把相应前端、后端、AI 检查加入 collab/team.json 的 checks 和 CI；当前协作测试不证明业务功能有效。

实际分支保护以GitHub设置为准。本次核查main没有分支保护；协作脚本和CI保留评审与测试检查，不能将约定描述为服务器已经强制保护。详见 [官方资料](docs/sources.md)。
