# 管理员配置：MiniDiva8

目标仓库：MiniDiva8/feiyi-xuanchuan，中文项目名“非遗宣传”，始终 private。
本地独立目录 D:/Codex/Projects/HeritageMarketingCollab。已有 AI创新大赛 项目保留。

## 已确认与待批准的远程操作
用户已确认创建这个私有仓库；任何重新授权须由本人确认。协作者邀请、首次上传及仓库设置以本次交付的实际授权记录为准，脚本不会因查看说明而执行。
创建 repo、上传 main、配置 settings、发送邀请、设置保护是独立命令，均须 --apply --confirm 完整仓库名。
默认 `python scripts/github_admin.py plan` 只打印方案，不连接 GitHub、不写远程。
不要运行完整命令清单来“试一下”；带 --apply 的命令会实际改变 GitHub。

## 1. 本人连接 GitHub
```powershell
gh auth login --hostname github.com --git-protocol https --web --clipboard
gh api user --jq .login
```
第二行应返回 MiniDiva8。只在 GitHub 官方页面确认，不把密码、令牌或别人的登录文件放入项目。
如果提示令牌无效，由本人重新登录；不要复用 Fqin9 或另一名成员的授权。
如使用原生 Codex GitHub 插件，选择 MiniDiva8 连接。该连接不能自动代替 GitHub CLI 的认证。

## 2. 创建私有仓库
```powershell
python scripts/github_admin.py create --apply --confirm MiniDiva8/feiyi-xuanchuan
```
存在同名仓库时停止并保留原仓库。创建后读取 API，验证 full_name 和 private；不能将一次成功请求当作全部配置完成。

## 3. 审查本地文件后首次上传
确认本地 Git 根目录只覆盖 HeritageMarketingCollab，忽略项生效，测试通过，并已有可审查的本地提交。
```powershell
python scripts/github_admin.py publish-initial --apply --confirm MiniDiva8/feiyi-xuanchuan
```
它仅向**尚无任何分支的私有仓库**首次上传当前提交为 main，设置默认分支；不会覆盖已有项目或强推，不属于合并已有代码。
如果有分支、工作区有改动、连接身份错误或检查失败，会停止。不要用 --force 绕过。

## 4. 议题、PR 与仓库设置
```powershell
python scripts/github_admin.py configure --apply --confirm MiniDiva8/feiyi-xuanchuan
```
启用 Issues，禁用 wiki、自动合并、merge commit/rebase merge，保留 Squash merge；合并后删除已合并分支，并创建区域、状态及共享范围标签。

## 5. 邀请两位成员
```powershell
python scripts/github_admin.py invite --apply --confirm MiniDiva8/feiyi-xuanchuan
```
仅邀请 donghaochen45-pixel 与 zhupaifan，权限为 write（API 名称 push）；不会授予仓库所有权或共享登录。
脚本检查已有协作者和待接受邀请，避免重复发送。
个人私有仓库的协作者是 write 角色；若以后需要精细的 read/triage/maintain 角色，再考虑组织仓库。
也可到仓库 Settings > Collaborators > Add people 手动邀请。两人必须各自登录并接受，邀请已发不等于权限已生效。

## 6. 主分支强制保护
```powershell
python scripts/github_admin.py protect --apply --confirm MiniDiva8/feiyi-xuanchuan
```
要求 collab-quality 通过、分支最新、至少一位同伴与 CODEOWNERS 审批、解决讨论；禁止强推和删除，管理员也受保护。
先让 CI 至少运行一次，核对实际 check 名称确为 collab-quality；在实际 GitHub 设置页确认保护有效。

**套餐边界：**官方文档说明，私有仓库分支保护需要 GitHub Pro/Team/Enterprise 等支持计划。Free 私有仓库可协作，但这些强制项可能不可用。
403/功能不可用时，脚本明确失败；保持私有，不购买、不转公开、不伪称保护已启用。可先执行人工合并约定；若希望服务器强制拦截，需所有者自行决定支持计划。
共享改动“两位同伴审批”另由 check-pr 工具和团队约定核对；单个全局保护规则的最低一票不等于强制两票。

## 7. Codex GitHub 授权与 Code Review（分别配置）
在各人的 Codex Cloud 环境创建流程选择仓库，出现 GitHub 连接要求时由本人确认。
仓库所有者如需批准/安装 GitHub App，只给本仓库必要访问；实际授权范围必须在官方界面查看。
可选 Codex 自动代码审查在官方 Code Review 设置中单独开启。AI 审查是补充，不代替另一名真人审批；本套件不自动发布 @codex 评论。
创建/发布一个人的 Cloud 环境，不能代替其他两人的个人授权和环境发布。

## 8. 首次端到端验收
每人各建一个小 Issue（使用模板，设置唯一 Assignee），在自己的个人 Cloud 环境开始，分别修改自己的模块并提交草稿 PR。
每个 PR 实际等待 Actions，解除草稿，其他成员评审；运行 check-pr 后由人逐个合并。
合并过程中后续 PR 如落后 main，回自己的分支 sync、检查、普通 push、重新审批。
最后三人各开一个新任务，记录 fetch 后 main SHA，并确认包含已合并变化。把证据填入 verification.md。
不要为了“测试完成”自动合并真实 PR，或用一个账户模拟另外两人的真实身份。
