# 非遗宣传：三人 GitHub + Codex Cloud 协作设计

用户要求直接创建并测试配置；保留当前项目。新套件独立放在 D:/Codex/Projects/HeritageMarketingCollab。
远程目标经用户确认：MiniDiva8/feiyi-xuanchuan，private。成员 MiniDiva8、donghaochen45-pixel、zhupaifan；Fqin9 不参与。
创建仓库已获用户确认；CLI 重新授权仍须本人确认；协作者邀请及首次上传在交付可审查内容后单独确认。禁止公开、自动合并、服务器部署、账户凭据共享。

## 目标
每人用自己的账号、自己的 Cloud environment 和隔离任务；GitHub 保存代码、Issue 分配、PR、评审与检查。
默认分工为前端、后端、AI，属于本套件建议，可在团队决定后修改 tracked team.json。
所有任务从最新 origin/main 开始；一个 Issue 一个负责人，一条独立分支，一个 PR。
共享接口或配置须在 Issue 获准扩展范围。阻止越界修改、跨人分支提交、脏目录切换、静默冲突处理、force push 和自动合并。

## 方案与边界
采用 GitHub 个人私有仓库 + 三份个人 Cloud 环境 + Python 标准库工具 + GitHub Actions。
个人仓库最少设置成本；组织仓库可后续迁移，但本次不创建组织。
不选 SSH/自建服务器/共享工作区；不采用自动合并，避免越过人的审查。
原生 Cloud PR/GitHub connector 为受支持的替代路线；不能假定连接器授权会自动让 gh CLI 登录。
Cloud 配置文件只是本项目脚本与提示，不声称可以自动创建/发布三个个人环境。

## 实现与验证
跨平台命令：doctor / start / save / preflight / sync / publish / check-pr / board。
所有 subprocess 使用参数数组，避免 shell 拼接；repo root 限定当前单一项目。
start 拉取 main 并记录基线；save 仅提交范围内明确文件；sync 先用 merge-tree 检查再同步自己的任务分支；publish 先检查私有仓库和身份，再普通 push、幂等创建 draft PR。
不重置工作区、不自动 stash、不强制推送。冲突检查不修改用户工作树。
离线仿真仅允许本地 bare remote，不允许对 GitHub remote 静默跳过身份与 Issue 核验。
CI 校验 Issue、分支、负责范围、测试；检查 PR 的最新头提交、至少一位其他成员的当前版本审批、实际 CI 结果。
私有仓库分支保护与 CODEOWNERS 强制能力取决于 GitHub 计划，失败须报告，不更改可见性或购买服务。

实测：临时 bare 仓库、三个独立 clone、真实提交/推送、独立集成 clone 的模拟 PR 合并、冲突无损拦截、后续新任务读取更新 main。
GitHub PR、Actions、三个人账户和三个实际 Cloud 环境单列验证状态，不将本地仿真当作云端验收。
