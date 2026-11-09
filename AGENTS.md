# 非遗宣传：三人协作规则

本仓库为 MiniDiva8/feiyi-xuanchuan 的三人协作基础配置。GitHub 是代码、任务分配、PR 和评审的统一来源。不得将另一名成员的本地目录或聊天记录视为最新代码。

## 每次开始任务
1. 先读本文件、负责目录下的 AGENTS.md，以及 collab/team.json。
2. 通过本人的 GitHub 连接读取目标 Issue，确认它仍开放、只有本人一个负责人，且验收标准和修改范围明确。一个 Issue 对应一条分支和一个 PR；不要重复认领已进行中的 Issue。
3. 检查 Git 根目录、分支、工作树和 git/gh 连接。工作树有未提交内容时保留原状；不要自动 stash、reset、clean 或切换到别人的分支。
4. 使用 `python scripts/collab.py start --member <a|b|c> --issue <编号> --slug <英文短名>`。它会拉取最新 origin/main，从该提交创建 codex/<GitHub登录名>/issue-<编号>-<短名> 分支，并记录起始提交。
5. 新的 Cloud 任务也必须实际拉取并核对 main；环境快照、缓存和“新任务”本身都不构成最新代码的证明。已有任务保留自己的状态。
6. Cloud 已连接 GitHub 而 gh 未认证时，不要复制任何人的凭据。用原生 GitHub 连接核验 Issue 后，可执行 start 的 --native --native-issue-verified 模式；明确记录核验依据。该标志表示由调用者完成核验，不是脚本自行认证。
7. --offline 仅适用于临时本地 bare 仓库仿真，不适用于真实 GitHub 开发。

## 三人共同代码权限（2026-11-08 所有者明确确认）
- MiniDiva8、donghaochen45-pixel、zhupaifan 三人都可以修改前端、后端、AI、契约、脚本、测试和文档等全部项目代码。
- collab/team.json 的 scope_mode=team-wide 是当前权限策略；members.module/paths 只表示主责参考，不构成路径禁令。
- 本条明确撤销各子目录 AGENTS.md 和历史文档中“只修改本模块”“不得修改另外两人模块”的旧权限限制。所有模块均以本条为准；子目录中的数据隔离、来源核验、技术及测试要求继续适用。
- 不因跨模块或修改公共目录要求 scope:shared-approved 或 --allow-shared；该标签/参数仅供旧 partitioned 策略兼容。
- 一项任务仍对应一个 Issue、一个负责人、本人分支及一个 PR；三人可做跨模块任务，先在 Issue 写清本次目标、路径和验收要求，避免同时改同一处代码。
- 保护凭据、运行数据库、依赖、构建产物、缓存与 Git 元数据；全目录代码权限不允许提交这些文件。
- CODEOWNERS 是评审责任，不是目录写入权限。三人共同拥有代码评审资格，作者本人不能替代同伴审批。

## 实现与交付
- 优先固定接口契约后并行实现；在 Issue 记录依赖、假设和阻塞。无需等待的模块继续独立推进。
- 先运行相关基线检查；添加能验证行为的测试。不得声称未运行的检查通过。
- 所有 Git 命令必须确认仓库根目录只覆盖这个项目。不要将 D:/Codex、用户主目录、Codex 运行时、AppData、依赖、缓存或大下载加入 Git。
- 不把 .env、私钥、账户登录信息或访问令牌放入代码、Issue、PR、日志或聊天；每个人单独管理授权。
- save 分别检查索引和工作树范围，运行 checks，再仅暂存明确列出的文件并提交；不要自行 git add -A。已有部分暂存文件时保留索引与工作文件，先显式确认如何处理。
- preflight 检查最新 main、范围与冲突，不改变工作树。start/sync 还会阻止新跟踪文件覆盖本地忽略文件。需要同步时用 sync，它先做无损冲突检查，再把 main 同步到本人的功能分支；不会 rebase/强推。
- 出现冲突时停止依赖修改，给出具体冲突文件与双方意图。禁止自动选择 ours/theirs 覆盖对方工作。
- publish 只做普通 push，并创建或复用草稿 PR；默认请求同伴评审。新增提交可再次 publish 复用原 PR。
- 没有 gh 登录时走 Cloud 原生 Create PR / GitHub 连接器；仍遵守分支名、Issue、范围和验证要求。
- 不自动合并、公开仓库、部署、变更授权或购买服务。任何合并由人明确决定。

## 审查与合并
team-wide 模式所有改动至少一位其他成员对当前 head 审批；旧 partitioned 模式共享范围仍需另外两位审批。审批应对应当前 PR head，新增提交后重新审查。
先结束草稿，再运行 `python scripts/collab.py check-pr --pr <编号>`。它核对当前 head、main、Issue、本次任务路径、评审和实际 CI；没有 CI、未知可合并性、旧审批都不是通过。
由人到 GitHub 执行 Squash and merge。当前检查只是状态快照；主分支变化后重新检查。
支持的 GitHub 计划可配置 main 分支保护，强制检查和审批；不支持时这些只是协作约定与检查工具，不能声称服务器已强制执行。

## 验证命令
`python -m unittest discover -s tests -v`
`python scripts/collab.py doctor`
`python scripts/simulate_team.py`（仅临时本地仿真，绝不等同三账户 Cloud 验收）

## Code Review Rules
- 重点检查多商家数据隔离：检索、文件、生成任务和报表必须绑定正确商家。
- 区分非遗来源事实、商家确认信息、AI 假设和未验证效果；不得编造传承人身份或宣传成效。
- 方案/素材审核绑定具体版本；文化表述或素材修改后重新审核，发布与复盘可追溯实际版本。
- 不允许通过改脚本、模板或 CI 绕过身份、敏感文件保护、检查和人工合并要求。CI 使用目标分支的策略核验权限，策略迁移本身也须评审。
