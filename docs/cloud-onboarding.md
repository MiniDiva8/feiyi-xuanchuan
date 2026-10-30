# 三个人分别连接 GitHub 与 Codex Cloud

核对日期：2026-10-30。本文使用当前 Cloud environments 文档中的桌面/Web 入口；不把 Legacy Code Review 环境当成通用的新 Cloud 开发环境。

## 每个人自己的配置

| 开发者 | GitHub | 成员键 | 建议个人环境名 |
|---|---|---|---|
| 你 | MiniDiva8 | a | feiyi-a-MiniDiva8 |
| 第二人 | donghaochen45-pixel | b | feiyi-b-donghaochen45-pixel |
| 第三人 | zhupaifan | c | feiyi-c-zhupaifan |

三个环境都连接同一个私有仓库 MiniDiva8/feiyi-xuanchuan，默认选 main。
每个人登录自己的 Codex/ChatGPT 账号、自己的 GitHub。环境选择 Only me；不需要共享环境或加入同一个 ChatGPT Enterprise 工作区。
“同仓库”不代表看到别人的未提交文件；每个任务使用独立工作区。

## A. GitHub 访问（每人分别做）
1. MiniDiva8 创建私有仓库，向另外两个账号发 write 邀请。
2. donghaochen45-pixel、zhupaifan 分别在自己的 GitHub 通知或邀请页面接受。接受后亲自打开私有仓库，确认能读取代码和看到 Issues/PR。
3. 在自己 Codex App 里使用自己的 GitHub 连接。若缺少访问，在官方授权页面按提示申请/授予本仓库的必要权限。
4. 仓库所有者可能需要为本仓库批准 GitHub App 安装/访问；每位使用者仍须建立自己的个人连接。
5. 插件“连接成功”、仓库 write、Cloud 可用性是不同检查。仓库列表没出现时检查登录账号、邀请是否接受、App 安装的仓库范围、组织政策（若以后迁移组织）。

不要复制任何人的 gh 配置、Codex 登录文件、Cookie、PAT 或 OAuth 凭据。仓库内容与授权需求可以共用，个人凭据不共用。

## B. 每人创建并发布个人 Cloud 环境
在 Windows Codex App 或 Web 操作：
1. 新任务选择 **Work in > Cloud**。
2. 打开 **Select environment > Create environment**。也可从 **Settings > Codex Cloud > Environments > Create environment** 进入。
3. 选择 **MiniDiva8/feiyi-xuanchuan**；如果提示 GitHub 登录，用本人的账号确认。
4. 选择 **Get started**，让 Codex 检查仓库和准备环境。
5. 提供下面的准备要求；检查设置报告、配置与实际测试结果。
6. 选择 **Save / Publish**，看到 **Environment published** 后再 **Start a new task**。
7. 另外两个人在各自账号重复以上步骤；不能用所有者的环境发布截图代替他们的验收。

可粘贴的准备要求：

```text
为 MiniDiva8/feiyi-xuanchuan 准备个人 Codex Cloud 开发环境。
保留 main 作为默认基线。使用 Python 3.11+、Git 2.38+，测试用 Python 标准库，不需要 API Key 或业务服务器。
检查仓库 AGENTS.md，运行 bash scripts/cloud-install.sh，并报告每条检查的实际结果。
如需要 GitHub CLI，请从官方来源安装。不要假设 GitHub 连接器授权等于 gh CLI 已认证；不要复制其他人的凭据。
Install script 可记录 bash scripts/cloud-install.sh。
Start skill 按 docs/cloud-start.md 做就绪检查；不要在环境准备阶段认领 Issue、创建开发分支或执行发布。
Who can use 设为 Only me。只允许实际需要的网络目的地，至少核实 github.com 和 api.github.com 的访问。
若缺少权限、运行时或工具，明确报告。检查完毕后等待我查看并发布环境。
```

本套件尚未选定前端/后端业务框架，不能声称已安装真实业务依赖。业务运行时确定后，更新 Install script，测试并 Republish。
保存只是配置保存；发布才提供给新任务使用。已有任务继续保留自己的状态。仓库 refresh 不等于重新执行安装/启动命令。

## C. 每个新任务读取最新代码
1. 先在 GitHub 用任务模板建立 Issue，填写验收与路径，把 Assignees 设为唯一负责人。
2. 在本人的已发布环境 **Start a new task**。
3. 使用 [a 的提示](prompts/member-a.md)、[b 的提示](prompts/member-b.md) 或 [c 的提示](prompts/member-c.md)，替换 Issue 编号和英文任务名。
4. 开始前真正 fetch origin/main，记录 SHA；运行 start 自动从该提交建分支。
5. 请 Codex 展示实际起点、负责范围、基线检查，随后实现、验证、提交并创建草稿 PR。授权只包括本 Issue 范围，不包括合并、公开、部署、改权限。

## D. Cloud 原生连接器与 gh 的两条路线
**CLI 路线：**本人 gh 已认证且 Git fetch/push 可用时，直接使用 collab.py 全流程。doctor 展示当前登录名，必须与成员键一致。
**原生路线：**若 Cloud GitHub 连接有效但 gh 不可用/未认证：
1. 用原生 GitHub 工具读取 Issue、核实唯一 Assignee 与范围；共享改动核实批准标签。
2. 确保环境自身的 Git 连接能 fetch；如果不能，先修复本人连接，不用离线标志绕过。
3. 执行 `start --native --native-issue-verified --member <成员键> --issue <编号> --slug <短名>`；如已批准共享范围再加 --allow-shared。
4. 用 save/preflight/sync 做本地工作，最后使用 Cloud 的 **Create PR** 或原生 GitHub 创建草稿 PR。PR 保留规范分支、Closes #Issue、检查证据。
5. 如原生 PR 功能不可用，只交付 diff 和 PR 文案，并明确“尚未创建 PR”；不能说已推送。
6. 另一位具备本人 gh 认证的成员可用 check-pr 读取 PR 状态，或在 GitHub 对照当前提交手工核验。

--native-issue-verified 是调用者对其已做的原生核验的显式声明，不是脚本自动认证。CI 会再检查 GitHub 实际分配与模块路径。
不把 gh 的个人 token 填进共享环境。当前 Cloud 支持个人值和网络秘密等设置，但本套件不要求手动提供长期 token。

## E. Windows 本地副本（可选）
三个人本地各 clone 一份，也可只用 Cloud。若要本地工作，安装官方 Git、Python、GitHub CLI，在本人的目录执行：

```powershell
gh auth login --hostname github.com --git-protocol https --web
gh repo clone MiniDiva8/feiyi-xuanchuan D:\Codex\Projects\feiyi-xuanchuan
cd D:\Codex\Projects\feiyi-xuanchuan
git config user.name "自己的GitHub用户名"
git config user.email "自己在GitHub设置中显示的noreply邮箱"
python scripts/collab.py doctor
```

只设置当前仓库的 Git 身份，不使用 --global 修改全机身份。Cloud 内也用本人确认的身份，不把示例文字当真实邮箱。
PowerShell 包装器被系统执行策略拦截时，直接用 python 命令；不要求更改全局 ExecutionPolicy。

## F. 每人实际验收
- 本人能看到并读取私有仓库。
- 本人个人环境发布成功；记录日期与环境名即可，不公开内部 ID 或访问令牌。
- 本人新任务 fetch 后记录 main SHA。
- 本人独立分支提交并创建 PR，GitHub 展示真实作者、head SHA 与 CI。
- 其他成员对最新 head 审批；由人决定是否合并。
- 合并后再次新开任务，确认 main 包含队友的变化。
将结果写进 verification.md。未做的项继续标未验证，不能因为本地仿真通过就打勾。
