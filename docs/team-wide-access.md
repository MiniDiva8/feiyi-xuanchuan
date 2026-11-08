# 三人共同代码权限 · 2026-11-08

所有者已明确确认：MiniDiva8、donghaochen45-pixel、zhupaifan都可以修改前端、后端、AI、契约、协作脚本、测试和文档。角色分工只是主责参考，不再作为路径写入限制。

## 这次解决的问题

GitHub上两位队友已经有write权限，邀请已接受；main未设置分支保护或ruleset。真正的操作障碍在项目中：

1. 原scope检查禁止跨成员目录，即使GitHub有写权限也无法通过save/CI。
2. 仓库已改公开，旧start/publish/board/check-pr/admin仍硬编码要求private，正常命令会报VISIBILITY。

配置现在明确使用 `scope_mode: team-wide`、`visibility: public`。脚本仍核验正确仓库和可见性，普通协作命令不更改公开状态。未配置新字段的旧策略仍按partitioned/private处理。

## 继续保留

- 一项任务一个Issue负责人、本人独立任务分支、一个PR，三个人可以分别做跨模块任务。
- 至少一名其他成员对当前head批准，实际CI通过后由人合并。新提交后的旧审批不能代替新head审批。
- 不自动合并，不自动覆盖冲突，不reset/stash/强推别人的改动。
- 禁止把密钥、账号会话、运行数据、依赖、构建与缓存提交到仓库。全代码权限不扩大到这些文件。
- 技术规范、商家隔离、文化事实来源和具体版本审核要求保留。

team-wide不需要因跨目录申请`scope:shared-approved`或使用`--allow-shared`。这两个入口保留兼容旧partitioned策略；旧模式对共享改动的两名同伴评审要求仍然有效。

根AGENTS明确撤销子目录历史“只改本模块”的限制，共同任务提示也已更新；子目录技术条款继续适用。本次迁移按main旧策略只改共享文件与前端负责人的说明，不通过HEAD策略给本PR自授权。CI仍读取BASE策略。本次迁移PR自身按旧共享规则评审，合并后新的普通跨模块PR按team-wide执行。

## 合并后怎样生效

**规则PR合并到main以后**，三人分别更新自己的工作区。仅刷新Codex页面或GitHub连接不会更新旧分支中的脚本和AGENTS。

- 新任务：先拉取最新main，再运行`python scripts/collab.py start --member a|b|c --issue 编号 --slug 短名`，使用自己的成员键和Issue。
- 已有脚本创建的任务分支：先保存当前修改，再运行`preflight`，无冲突后运行`sync`，将最新main合入本人分支。遇到冲突先停下核对双方意图。
- 旧手工分支没有`.collab/task.json`时，不伪造上下文；在本人干净分支中普通fetch并merge最新origin/main，或从最新main创建下一项任务。不得checkout或覆盖别人的工作分支。
- 各成员使用自己的GitHub/Codex连接。本次没有分享token，也没有将队友提升为管理员；修改代码所需的write权限本来已经具备。

## 验证

本地运行`python -m unittest discover -s tests -v`，包含旧分工模式、三成员跨目录真实Git提交、公开仓库在线start的模拟API、凭据/路径保护，以及当前head同伴审批和实际CI门槛。`python scripts/simulate_team.py`只在临时本地bare仓库做三克隆仿真，不等同于三个真实Cloud账号验收。

另实际使用当前所有者连接读取公开仓库board成功。没有在其他成员账号下代操作。main没有现成服务器分支保护；脚本/CI检查与团队评审约定不应表述成GitHub已强制拦截所有直接推送。
