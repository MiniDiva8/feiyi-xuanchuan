# 非遗宣传：三人协作规则

GitHub 是代码与协作状态的统一来源。默认使用 GitHub + Codex Cloud 原生能力；scripts/ 中已有工具保留为可选加强项，不是开始协作的前提。

## 每次任务开始
1. 读取本文件、对应目录的 AGENTS.md、collab/team.json 和 GitHub Issue。
2. 确认 Issue 开放、唯一负责人是本人的 GitHub 账号，检查已有分支/PR，避免重复实现。
3. 检查仓库根目录、分支和未提交改动。保留已有工作，不自动 stash、reset、clean，不操作别人的分支。
4. 实际拉取/刷新最新 origin/main，记录提交 SHA；不能把环境缓存、已发布快照或新建任务当成代码已最新的证明。
5. 从该基线创建 codex/<本人GitHub用户名>/issue-<编号>-<英文短名>。每人、每个任务都有独立工作区。
6. 只实现 Issue 约定范围，运行实际测试；提交、推送后用原生 Create PR 建草稿 PR，写 Closes #编号、起始 SHA、测试结果和未验证项。
7. 如 Cloud 无法读取仓库或创建 PR，由本人确认 GitHub 连接；不复制别人的凭据。不能把 diff 当成已创建的 PR。

## 负责范围
- MiniDiva8：apps/web/、docs/frontend/、tests/frontend/。
- donghaochen45-pixel：services/api/、docs/backend/、tests/backend/。
- zhupaifan：services/marketing-ai/、docs/ai/、tests/ai/。
- 以上为建议初始分工，调整须经团队确认，通过 PR 修改 team.json。
- 不直接改另一人的模块，包括删除与重命名原路径。跨模块功能拆成分别指派的 Issue/PR。
- packages/contracts/、根配置、.github/、scripts/、公共文档与公共测试属于共享范围；先在 Issue 写明影响与允许路径，获准后加 scope:shared-approved 标签。
- CODEOWNERS 是评审责任表，不是目录写权限 ACL。

## 评审、同步与合并
普通改动至少一位其他成员审查当前 head；共享改动由另外两位审查。新增提交后重新核对评审。
使用 GitHub 原生 PR 检查确认 collab-quality 实际通过且没有冲突；缺失、pending、未知状态都不算通过。
主分支有更新时，先保留自己的工作，再同步并处理冲突；不得强推或自动选择 ours/theirs 覆盖队友。
由人结束草稿并决定 Squash and merge。未经明确指令，不合并、不公开、不部署、不购买服务、不变更授权。
合并后新任务再次读取最新 main，已有任务保留自身状态。
私有 main 的强制分支保护是否生效，以 GitHub 实际设置为准；不支持时保留人工约定，不声称已经服务器强制执行。

## 验证与可选工具
协作基础测试：python -m unittest discover -s tests -v。
业务代码新增后补充对应前端、后端、AI 检查；本套件测试不证明业务功能有效。
可选 scripts/collab.py 提供范围检查、提交、同步、草稿 PR 与状态查询；CLI 认证与 Cloud GitHub 连接分别核实。
只在熟悉并需要时使用脚本。--offline 仅用于临时本地 bare 仓库仿真，不用于真实 GitHub 开发。

## 资料与凭据
每人独立保管 GitHub/Codex 登录。不得提交 .env、私钥、令牌、Codex 家目录、AppData、依赖目录或无关大文件。
Git 根目录只覆盖本项目；本地新工作按用户约定放 D:/Codex/Projects，独立交付放 D:/Codex/Outputs；Cloud 使用其提供的工作区。

## Code Review Rules
- 核对当前商家边界：资料检索、文件、生成任务和报表不能串用其他商家私有数据。
- 区分非遗来源事实、商家确认、AI 假设和未验证效果；不编造身份或宣传成效。
- 方案/素材审核绑定具体版本；修改后重新审核，发布与复盘能追溯实际版本。
